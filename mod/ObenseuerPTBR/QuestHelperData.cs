using System;
using System.Collections;
using System.Reflection;
using BepInEx.Bootstrap;
using HarmonyLib;

namespace ObenseuerPTBR
{
    /// <summary>
    /// Quest Helper's hint texts, requirement labels and Bazaar checkpoints come from a JSON file built into that mod,
    /// which it reads when it starts (before this plugin, a soft dependency). Once it has, the loaded texts are swapped
    /// for the catalog's "mod.QuestHelper:&lt;English&gt;" entries. The window's own labels are handled by ModStrings.
    /// </summary>
    internal static class QuestHelperData
    {
        // Text fields of Curated.Row, Need, Checkpoint and ChainTask. Ids, task keys and asset paths are left alone.
        private static readonly string[] TextFields = { "T1", "T2", "T3", "Title", "Note", "Where", "Label" };

        public static void Apply()
        {
            if (!Plugin.Enabled.Value || Plugin.Catalog == null || !Chainloader.PluginInfos.ContainsKey(ModStrings.QuestHelperGuid)) return;
            try
            {
                Type curated = AccessTools.TypeByName("QuestHelper.Curated");
                if (curated == null) return;
                int n = 0;
                foreach (string name in new[] { "Rows", "Checkpoints", "Chain" })
                {
                    object value = AccessTools.Field(curated, name)?.GetValue(null);
                    if (value is IDictionary dict) foreach (object o in dict.Values) n += Translate(o, 0);
                    else if (value is IEnumerable list) foreach (object o in list) n += Translate(o, 0);
                }
                Plugin.Log.LogInfo($"QuestHelper: translated {n} hint texts");
            }
            catch (Exception e)
            {
                Plugin.Log.LogWarning($"QuestHelper hints not translated: {e.Message}");
            }
        }

        private static int Translate(object o, int depth)
        {
            if (o == null || depth > 3) return 0;
            int n = 0;
            foreach (FieldInfo f in o.GetType().GetFields(BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic))
            {
                if (f.FieldType == typeof(string))
                {
                    if (Array.IndexOf(TextFields, f.Name) < 0 || !(f.GetValue(o) is string s) || s.Length == 0) continue;
                    if (Plugin.Catalog.TryKey("mod.QuestHelper:" + s, out string pt)) { f.SetValue(o, pt); n++; }
                }
                else if (typeof(IEnumerable).IsAssignableFrom(f.FieldType) && f.GetValue(o) is IEnumerable items)
                    foreach (object item in items) n += Translate(item, depth + 1);   // Needs, and a need's "any of"
            }
            return n;
        }
    }
}
