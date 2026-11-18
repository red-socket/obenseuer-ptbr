using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Reflection.Emit;
using System.Text.RegularExpressions;
using BepInEx.Bootstrap;
using HarmonyLib;

namespace ObenseuerPTBR
{
    /// <summary>
    /// Text of other mods that draw their own windows (Unity IMGUI), where no label hook can reach it, or that they
    /// build from small pieces (day names) no on-screen template can pick apart. Entries
    /// keyed "mod.&lt;Mod&gt;:&lt;English literal&gt;" in the catalog replace those string literals in the listed
    /// classes of that mod, once at load. Nothing happens when the mod is not installed, and a literal the mod
    /// no longer uses simply stays unused.
    /// </summary>
    internal static class ModStrings
    {
        private sealed class Target
        {
            public string Mod, Guid;
            public string[] Types;
            // Optional: only methods whose "Namespace.Type::Method" matches are changed. For mods that also use some of
            // the same words as internal keys ("done", "active"), so only the methods that build what you see are touched.
            public Regex Methods;
        }

        // Plugin.cs declares each of these GUIDs as a soft dependency, so the mod is loaded before this runs.
        internal const string BetterTenementGuid = "redsocket.obenseuer.bettertenement";
        internal const string FairMarketGuid = "redsocket.obenseuer.fairmarket";
        internal const string QuestHelperGuid = "redsocket.obenseuer.questhelper";

        private static readonly Target[] Targets =
        {
            new Target
            {
                Mod = "BetterTenement", Guid = BetterTenementGuid,
                Types = new[] { "BetterTenement.LedgerPanel", "BetterTenement.LedgerData", "BetterTenement.LedgerMath", "BetterTenement.LedgerCard" },
            },
            // Opening hours on shop doors: the day names and "closed" inside the weekly line. The sentence around them
            // ("(Closed, opens {0})") is an ordinary template in mods.po, matched on screen.
            new Target
            {
                Mod = "FairMarket", Guid = FairMarketGuid,
                Types = new[] { "FairMarket.Fmt", "FairMarket.Schedule" },
            },
            // The Quest Helper window (Unity IMGUI). Its hint texts come from a JSON file instead: see QuestHelperData.
            new Target
            {
                Mod = "QuestHelper", Guid = QuestHelperGuid,
                Types = new[]
                {
                    "QuestHelper.Strings", "QuestHelper.HelperWindow", "QuestHelper.DoctorTab", "QuestHelper.TaskListTab",
                    "QuestHelper.BazaarTab", "QuestHelper.Blockers", "QuestHelper.Lines", "QuestHelper.MapPin",
                    "QuestHelper.TbcSection", "QuestHelper.TbcHeaderHover", "QuestHelper.Toast", "QuestHelper.Pipeline",
                    "QuestHelper.RatProblem", "QuestHelper.CasinoCoup", "QuestHelper.ToivoLie", "QuestHelper.MiningPermit",
                    "QuestHelper.ElianaTalk", "QuestHelper.ButtonInfoPatch", "QuestHelper.Edits", "QuestHelper.Game",
                },
                Methods = new Regex(@"^QuestHelper\.(Strings::|HelperWindow::(Draw|HintsRow|FooterHint|Rebuild)$|DoctorTab::(BuildList|BuildDetail|BuildResult|StateText)$|TaskListTab(\+<>c__DisplayClass\d+_\d+)?::(Build|TaskRows|GroupTitle|<GenericObjectiveButton>b__\d+)$|BazaarTab::Build$|Blockers::Describe$|Lines::For$|MapPin::FindTarget$|TbcSection::Label$|TbcHeaderHover::OnPointerEnter$|Toast::Draw$|Pipeline::(Gates|RunFix|RunGeneric)$|(RatProblem|CasinoCoup|ToivoLie|MiningPermit|ElianaTalk)::(Detect|get_Title|Prepare)$|ButtonInfoPatch::Postfix$|Edits::GiveTaskItemIfMissing$|Game::MapName$)", RegexOptions.CultureInvariant),
            },
        };

        // The replacements for each patched method, for the transpiler (Harmony re-runs it whenever another patch lands on
        // the same method). Keys "mod.<Mod>:<literal>" apply in every method of the mod that is changed; keys
        // "mod.<Mod>:<Type>.<Method>|<literal>" only in that method, for words the mod also uses as internal keys.
        private static readonly Dictionary<MethodBase, Dictionary<string, string>> perMethod = new Dictionary<MethodBase, Dictionary<string, string>>();

        public static void Apply(Harmony harmony)
        {
            if (!Plugin.Enabled.Value || Plugin.Catalog == null) return;
            var counts = new Dictionary<string, int>(StringComparer.Ordinal);

            // Listed targets: every changed method of the listed types gets the mod's general keys.
            foreach (Target target in Targets)
            {
                if (!Chainloader.PluginInfos.ContainsKey(target.Guid)) continue;
                Dictionary<string, string> keys = Plugin.Catalog.KeysWithPrefix("mod." + target.Mod + ":");
                if (keys.Count == 0) continue;
                var map = new Dictionary<string, string>(StringComparer.Ordinal);
                var scoped = new Dictionary<string, Dictionary<string, string>>(StringComparer.Ordinal);
                foreach (var e in keys)
                {
                    int bar = e.Key.IndexOf('|');
                    if (bar < 0) { map[e.Key] = e.Value; continue; }
                    string where = e.Key.Substring(0, bar);
                    if (where.Contains("::")) continue;   // a method named in full: handled below
                    if (!scoped.TryGetValue(where, out var only)) scoped[where] = only = new Dictionary<string, string>(StringComparer.Ordinal);
                    only[e.Key.Substring(bar + 1)] = e.Value;
                }
                foreach (string typeName in target.Types)
                {
                    Type type = FindType(target.Mod, typeName);
                    if (type == null) continue;
                    ReplaceArrays(type, map);
                    foreach (MethodInfo m in Methods(type))
                    {
                        if (target.Methods != null && !target.Methods.IsMatch(m.DeclaringType.FullName + "::" + m.Name)) continue;
                        Add(m, map, target.Mod);
                        if (scoped.TryGetValue(m.DeclaringType.Name + "." + m.Name, out var only)) Add(m, only, target.Mod);
                    }
                }
            }

            // Keys that name their method in full, for any mod: "mod.<Mod>:<Namespace.Type>::<Method>|<literal>". The type
            // is only found when that mod is installed. "::.cctor" means a lookup table the type built when it loaded.
            foreach (var e in Plugin.Catalog.KeysWithPrefix("mod."))
            {
                int colon = e.Key.IndexOf(':'), sep = e.Key.IndexOf("::", StringComparison.Ordinal), bar = e.Key.IndexOf('|');
                if (colon < 0 || sep <= colon || bar <= sep) continue;
                string mod = e.Key.Substring(0, colon);
                Type type = FindType(mod, e.Key.Substring(colon + 1, sep - colon - 1));
                if (type == null) continue;
                string method = e.Key.Substring(sep + 2, bar - sep - 2), literal = e.Key.Substring(bar + 1);
                var one = new Dictionary<string, string>(StringComparer.Ordinal) { [literal] = e.Value };
                if (method == ".cctor") { ReplaceArrays(type, one); continue; }
                foreach (MethodInfo m in AccessTools.GetDeclaredMethods(type))
                    if (m.Name == method && m.GetMethodBody() != null && !m.ContainsGenericParameters) Add(m, one, mod);
            }

            // One transpiler per method, with everything that method should change.
            foreach (var e in perMethod.ToList())
            {
                try
                {
                    if (!UsesAny(e.Key, e.Value)) { perMethod.Remove(e.Key); continue; }
                    harmony.Patch(e.Key, transpiler: new HarmonyMethod(typeof(ModStrings), nameof(Transpiler)));
                    string mod = owner[e.Key];
                    counts[mod] = counts.TryGetValue(mod, out int n) ? n + 1 : 1;
                }
                catch (Exception ex)
                {
                    Plugin.Log.LogWarning($"{owner[e.Key]}: {e.Key.DeclaringType?.Name}.{e.Key.Name} not translated: {ex.Message}");
                }
            }
            foreach (var c in counts) Plugin.Log.LogInfo($"{c.Key}: translated text in {c.Value} methods");
        }

        private static readonly Dictionary<MethodBase, string> owner = new Dictionary<MethodBase, string>();

        // Types are looked up in the mod's own assembly (named like the mod), once each, missing ones included. Most of
        // the mods in mods.po are usually not installed: Harmony's AccessTools.TypeByName would scan every loaded type
        // and log a warning for each of hundreds of keys, which stalls the game's start.
        private static Dictionary<string, Assembly> assemblies;
        private static readonly Dictionary<string, Type> types = new Dictionary<string, Type>(StringComparer.Ordinal);

        internal static Type FindType(string mod, string typeName)
        {
            if (assemblies == null)
            {
                assemblies = new Dictionary<string, Assembly>(StringComparer.Ordinal);
                foreach (Assembly a in AppDomain.CurrentDomain.GetAssemblies())
                {
                    try { assemblies[a.GetName().Name] = a; }
                    catch (Exception) { }
                }
            }
            string key = mod + "/" + typeName;
            if (types.TryGetValue(key, out Type cached)) return cached;
            Type type = null;
            if (assemblies.TryGetValue(mod, out Assembly asm))
            {
                try { type = asm.GetType(typeName, false); }
                catch (Exception) { }
            }
            types[key] = type;
            return type;
        }

        private static void Add(MethodBase m, Dictionary<string, string> entries, string mod)
        {
            if (!perMethod.TryGetValue(m, out var map)) perMethod[m] = map = new Dictionary<string, string>(StringComparer.Ordinal);
            foreach (var e in entries) map[e.Key] = e.Value;
            owner[m] = mod;
        }

        // Lookup tables built in a static constructor ("Mon", "Tue", ...), which has usually run already: the array's
        // elements are replaced in place.
        private static void ReplaceArrays(Type type, Dictionary<string, string> map)
        {
            foreach (FieldInfo f in type.GetFields(BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic))
            {
                if (f.FieldType != typeof(string[]) || !(f.GetValue(null) is string[] values)) continue;
                for (int i = 0; i < values.Length; i++)
                    if (values[i] != null && map.TryGetValue(values[i], out string pt)) values[i] = pt;
            }
        }

        private static IEnumerable<MethodInfo> Methods(Type type)
        {
            foreach (MethodInfo m in AccessTools.GetDeclaredMethods(type))
                if (!m.IsAbstract && !m.ContainsGenericParameters && m.GetMethodBody() != null)
                    yield return m;
            foreach (Type nested in type.GetNestedTypes(BindingFlags.Public | BindingFlags.NonPublic))
                foreach (MethodInfo m in Methods(nested))
                    yield return m;
        }

        private static bool UsesAny(MethodBase m, Dictionary<string, string> map)
        {
            foreach (CodeInstruction ci in PatchProcessor.GetOriginalInstructions(m))
                if (ci.opcode == OpCodes.Ldstr && ci.operand is string s && map.ContainsKey(s))
                    return true;
            return false;
        }

        private static IEnumerable<CodeInstruction> Transpiler(IEnumerable<CodeInstruction> code, MethodBase original)
        {
            perMethod.TryGetValue(original, out var map);
            foreach (CodeInstruction ci in code)
            {
                if (map != null && ci.opcode == OpCodes.Ldstr && ci.operand is string s && map.TryGetValue(s, out string pt))
                    ci.operand = pt;
                yield return ci;
            }
        }
    }
}
