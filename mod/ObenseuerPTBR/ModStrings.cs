using System;
using System.Collections.Generic;
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
                    if (!scoped.TryGetValue(where, out var only)) scoped[where] = only = new Dictionary<string, string>(StringComparer.Ordinal);
                    only[e.Key.Substring(bar + 1)] = e.Value;
                }
                int methods = 0;
                foreach (string typeName in target.Types)
                {
                    Type type = AccessTools.TypeByName(typeName);
                    if (type == null) continue;
                    ReplaceArrays(type, map);
                    foreach (MethodInfo m in Methods(type))
                    {
                        try
                        {
                            if (target.Methods != null && !target.Methods.IsMatch(m.DeclaringType.FullName + "::" + m.Name)) continue;
                            var forMethod = map;
                            if (scoped.TryGetValue(m.DeclaringType.Name + "." + m.Name, out var only))
                            {
                                forMethod = new Dictionary<string, string>(map, StringComparer.Ordinal);
                                foreach (var e in only) forMethod[e.Key] = e.Value;
                            }
                            if (!UsesAny(m, forMethod)) continue;
                            perMethod[m] = forMethod;
                            harmony.Patch(m, transpiler: new HarmonyMethod(typeof(ModStrings), nameof(Transpiler)));
                            methods++;
                        }
                        catch (Exception e)
                        {
                            Plugin.Log.LogWarning($"{target.Mod}: {type.Name}.{m.Name} not translated: {e.Message}");
                        }
                    }
                }
                Plugin.Log.LogInfo($"{target.Mod}: translated text in {methods} methods");
            }
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

        private static bool UsesAny(MethodInfo m, Dictionary<string, string> map)
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
