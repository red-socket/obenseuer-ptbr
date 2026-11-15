using System.Globalization;
using System.Text.RegularExpressions;
using TMPro;
using UnityEngine;

namespace ObenseuerPTBR
{
    /// <summary>
    /// Keeps Portuguese (usually longer than the English) inside the space the game laid out for the English.
    /// A translation that needs more lines than the English, or is wider than a sign drawn for the English,
    /// is scaled down with a &lt;size=N%&gt; tag, never below a minimum.
    /// </summary>
    internal static class TextFit
    {
        private const float MinUiScale = 0.6f;
        private const float MinSignScale = 0.55f;
        private static readonly Regex Tag = new Regex("<[^<>]*>", RegexOptions.CultureInvariant);

        public static string Fit(TMP_Text label, string english, string pt)
        {
            if (label == null || label.font == null || label.enableAutoSizing || pt.IndexOf("<size", System.StringComparison.OrdinalIgnoreCase) >= 0)
                return pt;
            float en = Width(label, english), tr = Width(label, pt);
            if (en <= 0f || tr <= en * 1.02f)
                return pt;

            float scale = 1f;
            bool sign = label is TextMeshPro;   // world-space text: the sign was drawn for the English width
            float unit = label.fontSize * (label.isOrthographic ? 1f : 0.1f);
            float box = label.rectTransform.rect.width - label.margin.x - label.margin.z;
            if (sign)
                scale = Mathf.Max(MinSignScale, en / tr);
            else if (box <= 0f)
                return pt;
            else if (label.textWrappingMode == TextWrappingModes.NoWrap || label.textWrappingMode == TextWrappingModes.PreserveWhitespaceNoWrap)
            {
                if (tr * unit > box) scale = Mathf.Max(MinUiScale, box / (tr * unit));
            }
            else
            {
                int lines = Lines(label, english, unit, box, 1f);
                for (scale = 1f; scale > MinUiScale && Lines(label, pt, unit, box, scale) > lines; scale -= 0.05f) { }
                scale = Mathf.Max(MinUiScale, scale);
            }
            if (scale >= 0.99f)
                return pt;
            return "<size=" + Mathf.FloorToInt(scale * 100f).ToString(CultureInfo.InvariantCulture) + "%>" + pt;
        }

        /// <summary>
        /// A one-line button that auto-sizes with word wrap on wraps a longer Portuguese label into two tiny
        /// lines (or breaks a long word) instead of shrinking it. Turn wrapping off for those labels.
        /// </summary>
        public static void PreferOneLine(TMP_Text label)
        {
            if (!label.enableAutoSizing || label.textWrappingMode == TextWrappingModes.NoWrap) return;
            float h = label.rectTransform.rect.height - label.margin.y - label.margin.w;
            string text = label.text;
            if (h <= 0f || h >= label.fontSizeMax * 2f || (text != null && text.IndexOf('\n') >= 0)) return;
            label.textWrappingMode = TextWrappingModes.NoWrap;
        }

        // Estimated wrapped line count: each paragraph's width over the box, at a given size scale.
        private static int Lines(TMP_Text label, string text, float unit, float box, float scale)
        {
            int lines = 0;
            foreach (string para in Tag.Replace(text, "").Split('\n'))
            {
                float w = Width(label, para) * unit * scale;
                lines += Mathf.Max(1, Mathf.CeilToInt(w / (box * 0.97f)));
            }
            return lines;
        }

        /// <summary>Width of the longest line in em (multiples of the font size), as TMP lays it out.</summary>
        private static float Width(TMP_Text label, string s)
        {
            s = Tag.Replace(s, "");
            FontStyles style = label.fontStyle;
            if ((style & (FontStyles.UpperCase | FontStyles.SmallCaps)) != 0) s = s.ToUpperInvariant();
            else if ((style & FontStyles.LowerCase) != 0) s = s.ToLowerInvariant();
            float spacing = label.characterSpacing * 0.01f, max = 0f, line = 0f;
            foreach (char c in s)
            {
                if (c == '\n') { max = Mathf.Max(max, line); line = 0f; continue; }
                line += Advance(label.font, c) + spacing;
            }
            return Mathf.Max(max, line);
        }

        private static float Advance(TMP_FontAsset font, char c)
        {
            TMP_Character ch = TMP_FontAssetUtilities.GetCharacterFromFontAsset(c, font, true, FontStyles.Normal, FontWeight.Regular, out _);
            if (ch == null || ch.glyph == null) return 0.5f;
            var owner = ch.textAsset as TMP_FontAsset ?? font;
            float point = owner.faceInfo.pointSize;
            if (point <= 0f) return 0.5f;
            return ch.glyph.metrics.horizontalAdvance * ch.glyph.scale * owner.faceInfo.scale / point;
        }
    }
}
