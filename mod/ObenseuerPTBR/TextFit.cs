using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text.RegularExpressions;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

namespace ObenseuerPTBR
{
    /// <summary>
    /// Keeps Portuguese (usually longer than the English) inside the space the game laid out for the English.
    /// A one-line label centred in a wider parent (a button whose label box was sized for the English word)
    /// is widened first. A translation that still needs more lines than the English, or is wider than a sign
    /// drawn for the English, is scaled down with a &lt;size=N%&gt; tag, never below a minimum.
    /// </summary>
    internal static class TextFit
    {
        private const float MinUiScale = 0.6f;
        private const float MinSignScale = 0.55f;
        private const float Gutter = 6f;   // space kept between a widened label and its parent's edges
        private static readonly Regex Tag = new Regex("<[^<>]*>", RegexOptions.CultureInvariant);

        // Label resizes are applied on the next frame, outside TMP's text generation.
        private static readonly Dictionary<int, Action> pending = new Dictionary<int, Action>();
        private static readonly HashSet<int> widened = new HashSet<int>();   // each label is widened at most once

        public static void ApplyPending()
        {
            if (pending.Count == 0) return;
            var actions = new List<Action>(pending.Values);
            pending.Clear();
            foreach (Action a in actions)
            {
                try { a(); }
                catch (Exception e) { Plugin.Log.LogDebug($"Label resize skipped: {e.Message}"); }
            }
        }

        public static string Fit(TMP_Text label, string english, string pt)
        {
            if (label == null || label.font == null || pt.IndexOf("<size", StringComparison.OrdinalIgnoreCase) >= 0)
                return pt;
            if (SizedByLayout(label))
                return pt;   // the layout already sizes the box to the text; fitting would fight it
            float en = Width(label, english), tr = Width(label, pt);
            if (en <= 0f || tr <= en * 1.02f)
                return pt;
            if (TryWiden(label, english, tr))
                return pt;
            if (label.enableAutoSizing)
            {
                LowerMinSize(label, tr);
                return pt;
            }

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
                // The English was laid out to fit, so count its lines leniently and the Portuguese strictly.
                int lines = Lines(label, english, unit, box * 1.03f, 1f);
                for (scale = 1f; scale > MinUiScale && Lines(label, pt, unit, box * 0.94f, scale) > lines; scale -= 0.05f) { }
                scale = Mathf.Max(MinUiScale, scale);
            }
            if (scale >= 0.99f)
                return pt;
            if (!label.richText)
            {
                // The size tag needs rich text. Turn it on only when the text has no '<' that would start parsing.
                if (pt.IndexOf('<') >= 0 || english.IndexOf('<') >= 0) return pt;
                label.richText = true;
            }
            return "<size=" + Mathf.FloorToInt(scale * 100f).ToString(CultureInfo.InvariantCulture) + "%>" + pt;
        }

        /// <summary>
        /// An auto-sizing one-line label stops shrinking at its minimum size and cuts the text with an ellipsis.
        /// If the translation is too wide even at the minimum, lower the minimum (not below 60% of it).
        /// </summary>
        private static void LowerMinSize(TMP_Text label, float widthEm)
        {
            if (label.textWrappingMode != TextWrappingModes.NoWrap && !IsOneLine(label)) return;
            float box = label.rectTransform.rect.width - label.margin.x - label.margin.z;
            if (box <= 0f || widthEm <= 0f) return;
            float needed = box / widthEm * 0.97f;
            if (needed >= label.fontSizeMin) return;
            float min = Mathf.Max(label.fontSizeMin * MinUiScale, needed);
            pending[label.GetInstanceID()] = () =>
            {
                if (label == null) return;
                label.fontSizeMin = min;
                label.ForceMeshUpdate(false, true);
            };
        }

        /// <summary>
        /// A one-line button that auto-sizes with word wrap on wraps a longer Portuguese label into two tiny
        /// lines (or breaks a long word) instead of shrinking it. Turn wrapping off for those labels.
        /// </summary>
        public static void PreferOneLine(TMP_Text label)
        {
            if (!label.enableAutoSizing || label.textWrappingMode == TextWrappingModes.NoWrap) return;
            if (IsOneLine(label)) label.textWrappingMode = TextWrappingModes.NoWrap;
        }

        /// <summary>
        /// True when the label's width follows its own text: a content size fitter on the label, a parent layout
        /// group that sizes children to their preferred width, or one whose own fitter sizes it to its children.
        /// Fitting such a label would fight the layout and flicker. Fixed cells (the blueprint table, which has
        /// no layout group) still get fitted.
        /// </summary>
        public static bool SizedByLayout(TMP_Text label)
        {
            if (FitsWidth(label.GetComponent<ContentSizeFitter>())) return true;
            Transform parent = label.transform.parent;
            if (parent == null) return false;
            var group = parent.GetComponent<HorizontalOrVerticalLayoutGroup>();
            if (group == null || !group.enabled || !group.childControlWidth) return false;
            // The group gives the label its preferred (text) width when it doesn't stretch children to fill,
            // or when a fitter sizes the group itself to its children (furniture info panel, main menu).
            return !group.childForceExpandWidth || FitsWidth(parent.GetComponent<ContentSizeFitter>());
        }

        private static bool FitsWidth(ContentSizeFitter f) =>
            f != null && f.enabled && f.horizontalFit != ContentSizeFitter.FitMode.Unconstrained;

        // Too short for two lines at the label's authored size, and the English is a single line.
        private static bool IsOneLine(TMP_Text label)
        {
            float h = label.rectTransform.rect.height - label.margin.y - label.margin.w;
            float size = label.enableAutoSizing ? Mathf.Min(label.fontSizeMax, label.fontSize) : label.fontSize;
            string text = label.text;
            return h > 0f && size > 0f && h < size * 2.4f && (text == null || text.IndexOf('\n') < 0);
        }

        /// <summary>
        /// Widens a one-line UI label that is centred in its parent and inset from its edges, so the translation
        /// fits on one line at the label's full size. Returns true if a resize was scheduled.
        /// </summary>
        private static bool TryWiden(TMP_Text label, string english, float widthEm)
        {
            if (label is TextMeshPro || english.IndexOf('\n') >= 0 || widened.Contains(label.GetInstanceID())
                || SizedByLayout(label) || !IsOneLine(label)) return false;
            RectTransform rt = label.rectTransform;
            if (!(rt.parent is RectTransform parent) || rt.anchorMin.x != 0f || rt.anchorMax.x != 1f
                || Mathf.Abs(rt.pivot.x - 0.5f) > 0.01f || Mathf.Abs(rt.anchoredPosition.x) > 1f || rt.sizeDelta.x >= -Gutter)
                return false;
            float size = label.enableAutoSizing ? label.fontSizeMax : label.fontSize;
            float needed = widthEm * size + label.margin.x + label.margin.z + 2f;
            float extra = needed - rt.rect.width;
            if (extra <= 0f) return false;
            float newDelta = Mathf.Min(-Gutter, rt.sizeDelta.x + extra);
            if (newDelta <= rt.sizeDelta.x + 0.5f) return false;
            if (CoversIcon(rt, needed)) return false;
            widened.Add(label.GetInstanceID());
            pending[label.GetInstanceID()] = () =>
            {
                if (label == null) return;
                rt.sizeDelta = new Vector2(newDelta, rt.sizeDelta.y);
                label.ForceMeshUpdate(false, true);
            };
            return true;
        }

        // Widening must not slide the text under an icon beside it (sleep screen: "Cancelar" next to its button
        // glyph). Graphics that enclose the whole label are its background and don't count.
        private static bool CoversIcon(RectTransform rt, float textWidth)
        {
            Rect label = WorldRect(rt);
            float half = textWidth * 0.5f * rt.lossyScale.x;
            Rect text = Rect.MinMaxRect(label.center.x - half, label.yMin, label.center.x + half, label.yMax);
            foreach (Graphic g in rt.parent.GetComponentsInChildren<Graphic>(false))
            {
                if (g.transform == rt || g.transform.IsChildOf(rt) || !g.enabled || g is TMP_Text) continue;
                Rect r = WorldRect(g.rectTransform);
                bool encloses = r.xMin <= label.xMin + 1f && r.xMax >= label.xMax - 1f && r.yMin <= label.yMin + 1f && r.yMax >= label.yMax - 1f;
                if (!encloses && r.Overlaps(text)) return true;
            }
            return false;
        }

        private static readonly Vector3[] corners = new Vector3[4];

        private static Rect WorldRect(RectTransform rt)
        {
            rt.GetWorldCorners(corners);
            return Rect.MinMaxRect(corners[0].x, corners[0].y, corners[2].x, corners[2].y);
        }

        // Estimated wrapped line count: each paragraph's width over the (adjusted) box, at a given size scale.
        private static int Lines(TMP_Text label, string text, float unit, float box, float scale)
        {
            int lines = 0;
            foreach (string para in Tag.Replace(text, "").Split('\n'))
            {
                float w = Width(label, para) * unit * scale;
                lines += Mathf.Max(1, Mathf.CeilToInt(w / box));
            }
            return lines;
        }

        /// <summary>Width of the longest line in em (multiples of the font size), as TMP lays it out.</summary>
        internal static float Width(TMP_Text label, string s)
        {
            s = Tag.Replace(s, "");
            FontStyles style = label.fontStyle;
            if ((style & (FontStyles.UpperCase | FontStyles.SmallCaps)) != 0) s = s.ToUpperInvariant();
            else if ((style & FontStyles.LowerCase) != 0) s = s.ToLowerInvariant();
            float spacing = label.characterSpacing * 0.01f, max = 0f, line = 0f;
            if ((style & FontStyles.Bold) != 0) spacing += label.font.boldSpacing * 0.01f;   // TMP widens bold glyphs
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
