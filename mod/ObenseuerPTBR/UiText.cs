using System;
using System.Collections.Generic;
using System.IO;
using HarmonyLib;
using TMPro;
using UnityEngine;

namespace ObenseuerPTBR
{
    /// <summary>
    /// Translates TextMeshPro labels when they are drawn. A TMP ITextPreprocessor changes only what the
    /// player sees: TMP_Text.text stays English, so game code that reads labels back (the options menu
    /// compares screen mode and quality labels with "Windowed" and "Custom") keeps working.
    /// </summary>
    internal sealed class UiText : ITextPreprocessor
    {
        private static readonly HashSet<string> missing = new HashSet<string>(StringComparer.Ordinal);
        private static bool failed;

        private readonly TMP_Text label;

        private UiText(TMP_Text label)
        {
            this.label = label;
        }

        public string PreprocessText(string text)
        {
            if (!Plugin.Enabled.Value || string.IsNullOrEmpty(text) || Plugin.Translator == null)
                return text;
            try
            {
                string pt = Plugin.Translator.Translate(text);
                if (pt != null)
                    return TextFit.Fit(label, text, GenderMarkers.Resolve(pt));
                string resolved = GenderMarkers.Resolve(text);   // dialogue arrives already in Portuguese
                if (!ReferenceEquals(resolved, text))
                    return resolved;
                Collect(text.Trim());
                return text;
            }
            catch (Exception e)
            {
                if (!failed) Plugin.Log.LogError($"UI text translation failed, showing English: {e}");
                failed = true;
                return text;
            }
        }

        /// <summary>Attaches the preprocessor to one label, unless it shows text the player types.</summary>
        public static void Attach(TMP_Text label)
        {
            if (label == null || label.textPreprocessor != null) return;   // ours already, or someone else's
            var input = label.GetComponentInParent<TMP_InputField>(true);
            if (input != null && input.textComponent == label) return;
            TextFit.PreferOneLine(label);
            label.textPreprocessor = new UiText(label);
            label.havePropertiesChanged = true;
            label.SetVerticesDirty();
        }

        /// <summary>Labels that woke before the plugin (or are inactive) get the preprocessor here.</summary>
        public static void AttachAll()
        {
            foreach (TMP_Text label in Resources.FindObjectsOfTypeAll<TMP_Text>())
                if (label.gameObject.scene.IsValid())
                    Attach(label);
        }

        // Writes each English UI string that had no translation to a file, so translators can find gaps.
        private static void Collect(string text)
        {
            if (!Plugin.CollectUntranslated.Value || text.Length < 2 || !HasLetters(text)
                || Plugin.Catalog.IsTranslation(text) || !missing.Add(text))
                return;
            try { File.AppendAllText(Plugin.UntranslatedPath, "msgid \"" + Escape(text) + "\"\nmsgstr \"\"\n\n"); }
            catch (IOException) { }
        }

        private static bool HasLetters(string s)
        {
            int letters = 0;
            foreach (char c in s)
                if (char.IsLetter(c) && ++letters >= 2) return true;
            return false;
        }

        private static string Escape(string s) =>
            s.Replace("\\", "\\\\").Replace("\"", "\\\"").Replace("\n", "\\n").Replace("\t", "\\t");
    }

    [HarmonyPatch]
    internal static class TmpAwakePatch
    {
        private static IEnumerable<System.Reflection.MethodBase> TargetMethods()
        {
            yield return AccessTools.Method(typeof(TextMeshProUGUI), "Awake");
            yield return AccessTools.Method(typeof(TextMeshPro), "Awake");
        }

        private static void Postfix(TMP_Text __instance) => UiText.Attach(__instance);
    }
}
