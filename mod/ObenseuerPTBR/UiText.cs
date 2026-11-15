using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using System.Text.RegularExpressions;
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
                Collect(text.Trim(), label);
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

        // Writes each English UI string that had no translation to a file, with the scene and object path
        // it appeared on, so translators can find gaps. Text that is already Portuguese (dialogue arrives
        // translated) is skipped.
        private static void Collect(string text, TMP_Text label)
        {
            if (!Plugin.CollectUntranslated.Value || text.Length < 2 || !HasLetters(text)
                || Plugin.Catalog.IsTranslation(text) || LooksPortuguese(text) || !missing.Add(text))
                return;
            try
            {
                string where = label == null ? "?" : label.gameObject.scene.name + ": " + PathOf(label.transform);
                File.AppendAllText(Plugin.UntranslatedPath,
                    "#: " + where + "\nmsgid \"" + Escape(text) + "\"\nmsgstr \"\"\n\n", Encoding.UTF8);
            }
            catch (IOException) { }
        }

        private static readonly Regex PtWords = new Regex(@"\b(você|não|que|para|com|uma|um|está|isso|esse|essa|aqui|sim|meu|minha|seu|sua|ele|ela|eu|tem|vai|pra|mais|muito|do|da|dos|das|no|na|os|as|é)\b",
            RegexOptions.IgnoreCase | RegexOptions.CultureInvariant);
        private static readonly Regex EnWords = new Regex(@"\b(the|you|and|is|to|of|in|it|that|for|with|this|your|are|not|have|was|be|on|at|my|me|we|do|what|can)\b",
            RegexOptions.IgnoreCase | RegexOptions.CultureInvariant);

        private static bool LooksPortuguese(string s)
        {
            if (s.IndexOfAny("ãõçáéíóúâêôàÃÕÇÁÉÍÓÚÂÊÔÀ".ToCharArray()) >= 0) return true;
            return PtWords.Matches(s).Count > EnWords.Matches(s).Count;
        }

        private static string PathOf(Transform t)
        {
            var sb = new StringBuilder(t.name);
            for (Transform p = t.parent; p != null; p = p.parent) sb.Insert(0, p.name + "/");
            return sb.ToString();
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
