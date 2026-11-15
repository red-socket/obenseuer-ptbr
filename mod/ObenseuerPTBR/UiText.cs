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
        private readonly TMP_InputField input;   // set when the label shows an input field's text

        // Flicker guard: a label whose fit keeps flipping (the layout reacts to our size tag) is left unshrunk.
        private string lastEnglish, lastShown, previousShown, settled;
        private int flips;

        private UiText(TMP_Text label, TMP_InputField input)
        {
            this.label = label;
            this.input = input;
        }

        public string PreprocessText(string text)
        {
            if (!Plugin.Enabled.Value || string.IsNullOrEmpty(text) || Plugin.Translator == null)
                return text;
            if (input != null && input.isFocused)
                return text;   // the player is typing: show exactly what is in the field
            try
            {
                string pt = Scoped(text) ?? Plugin.Translator.Translate(text);
                if (pt != null)
                    return Stable(text, TextFit.Fit(label, text, GenderMarkers.Resolve(pt)), GenderMarkers.Resolve(pt));
                string resolved = GenderMarkers.Resolve(text);   // dialogue arrives already in Portuguese
                if (!ReferenceEquals(resolved, text))
                    return resolved;
                if (input == null)
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

        // Context entries (manual.po): msgctxt "scope:<object name>:<English>" for the label's own object or one of
        // its three nearest parents, e.g. "scope:Use Button Disabled:Drink" -> "Beber" while the item type "Drink"
        // elsewhere stays "Bebida".
        private string Scoped(string text)
        {
            Transform t = label.transform;
            for (int i = 0; i < 4 && t != null; i++, t = t.parent)
                if (Plugin.Catalog.TryKey("scope:" + t.name + ":" + text, out string pt))
                    return pt;
            return null;
        }

        private string Stable(string english, string fitted, string plain)
        {
            if (settled == english) return plain;
            if (english == lastEnglish && fitted != lastShown && fitted == previousShown && ++flips >= 2)
            {
                settled = english;
                return plain;
            }
            if (english != lastEnglish) flips = 0;
            previousShown = lastShown;
            lastShown = fitted;
            lastEnglish = english;
            return fitted;
        }

        /// <summary>Attaches the preprocessor to one label (input fields too: only their displayed text changes).</summary>
        public static void Attach(TMP_Text label)
        {
            if (label == null || label.textPreprocessor != null) return;   // ours already, or someone else's
            var input = label.GetComponentInParent<TMP_InputField>(true);
            if (input != null && input.textComponent != label) input = null;
            TextFit.PreferOneLine(label);
            label.textPreprocessor = new UiText(label, input);
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
