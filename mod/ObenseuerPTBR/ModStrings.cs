using System;
using System.Collections.Generic;
using System.Reflection;
using System.Reflection.Emit;
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
        }

        // Plugin.cs declares each of these GUIDs as a soft dependency, so the mod is loaded before this runs.
        internal const string BetterTenementGuid = "redsocket.obenseuer.bettertenement";
        internal const string FairMarketGuid = "redsocket.obenseuer.fairmarket";

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
        };

        // Every replacement, for the transpiler (Harmony re-runs it whenever another patch lands on the same method).
        private static readonly Dictionary<string, string> all = new Dictionary<string, string>(StringComparer.Ordinal);

        public static void Apply(Harmony harmony)
        {
            if (!Plugin.Enabled.Value || Plugin.Catalog == null) return;
            foreach (Target target in Targets)
            {
                if (!Chainloader.PluginInfos.ContainsKey(target.Guid)) continue;
                Dictionary<string, string> map = Plugin.Catalog.KeysWithPrefix("mod." + target.Mod + ":");
                if (map.Count == 0) continue;
                foreach (var e in map) all[e.Key] = e.Value;
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
                            if (!UsesAny(m, map)) continue;
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

        private static IEnumerable<CodeInstruction> Transpiler(IEnumerable<CodeInstruction> code)
        {
            foreach (CodeInstruction ci in code)
            {
                if (ci.opcode == OpCodes.Ldstr && ci.operand is string s && all.TryGetValue(s, out string pt))
                    ci.operand = pt;
                yield return ci;
            }
        }
    }
}
