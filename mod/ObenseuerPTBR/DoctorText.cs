using System;
using System.Collections.Generic;
using System.Reflection;
using HarmonyLib;

namespace ObenseuerPTBR
{
    /// <summary>
    /// The doctor's addiction diagnosis is glued together from English pieces ("You're very addicted to " +
    /// "green mushrooms" + " and " + ...), which no per-string translation can turn into Portuguese. After the
    /// game builds it, the same diagnosis is rebuilt from the catalog's "doctor.*" entries, using the game's own
    /// addiction levels. If any entry is missing, the English stays.
    /// </summary>
    [HarmonyPatch(typeof(TreatmentAddictions), nameof(TreatmentAddictions.GetDescription))]
    internal static class DoctorDiagnosisPatch
    {
        // TreatmentAddictions.AddictionLevel (private): None, Moderate, Normal, High, Widthdrawal.
        private const int Moderate = 1, Normal = 2, High = 3, Withdrawal = 4;
        private static readonly string[] Addictions = { "mushroom", "alcohol", "smoking", "gambling" };

        private static readonly MethodInfo LevelOf = AccessTools.Method(typeof(TreatmentAddictions), "GetAddictionLevel");

        private static void Postfix(TreatmentAddictions __instance, ref string __result)
        {
            if (!Plugin.Enabled.Value || Plugin.Catalog == null || LevelOf == null) return;
            try
            {
                string pt = Build(__instance);
                if (pt != null) __result = GenderMarkers.Resolve(pt);
            }
            catch (Exception e)
            {
                Plugin.Log.LogWarning($"Doctor diagnosis not translated: {e.Message}");
            }
        }

        private static string Build(TreatmentAddictions treatment)
        {
            PlayerStats stats = PlayerStats.instance;
            var parts = new List<string>();
            if (stats.alcohol.AlcoholInBlood > 20f) parts.Add(Key("doctor.drinking"));
            else if (stats.mushrooms.MushroomsHigh > 10f) parts.Add(Key("doctor.mushrooms"));

            float[] values = { stats.addictions.MushroomAddiction, stats.addictions.AlcoholAddiction,
                               stats.addictions.SmokingAddiction, stats.addictions.GamblingAddiction };
            int[] levels = new int[values.Length];
            for (int i = 0; i < values.Length; i++)
                levels[i] = Convert.ToInt32(LevelOf.Invoke(treatment, new object[] { values[i] }));

            // Same order as the game: withdrawal, high, normal, moderate.
            foreach (var (level, sentence) in new[] { (Withdrawal, "doctor.withdrawal"), (High, "doctor.high"), (Normal, "doctor.normal"), (Moderate, "doctor.moderate") })
            {
                var names = new List<string>();
                for (int i = 0; i < levels.Length; i++)
                    if (levels[i] == level) names.Add(Key("doctor.name." + Addictions[i]));
                if (names.Count == 0) continue;
                string template = Key(sentence), list = Join(names);
                parts.Add(template == null || list == null ? null : string.Format(template, list));
            }
            if (parts.Count == 0) parts.Add(Key("doctor.none"));
            return parts.Contains(null) ? null : string.Join(" ", parts);
        }

        // "a", "a e b", "a, b e c"
        private static string Join(List<string> names)
        {
            if (names.Contains(null)) return null;
            if (names.Count == 1) return names[0];
            string and = Key("doctor.and") ?? " e ";
            return string.Join(", ", names.GetRange(0, names.Count - 1)) + and + names[names.Count - 1];
        }

        private static string Key(string key) => Plugin.Catalog.TryKey(key, out string pt) ? pt : null;
    }
}
