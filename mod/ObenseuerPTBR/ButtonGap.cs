using TMPro;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace ObenseuerPTBR
{
    /// <summary>
    /// Pairs of buttons placed side by side by hand ("Next" then "Back" on the character creation panels), each sized to
    /// its own text. A longer Portuguese label on the left button grows into the right one ("PRÓXIMOVOLTAR"), so the
    /// right button is moved along by as much as the left label grew, keeping the gap the English had.
    /// </summary>
    internal static class ButtonGap
    {
        private static readonly string[][] Pairs = { new[] { "Next", "Back" } };

        public static void Apply(Scene scene)
        {
            if (!Plugin.Enabled.Value || Plugin.Translator == null) return;
            foreach (GameObject root in scene.GetRootGameObjects())
                foreach (RectTransform right in root.GetComponentsInChildren<RectTransform>(true))
                    foreach (string[] pair in Pairs)
                    {
                        if (right.name != pair[1] || right.parent == null) continue;
                        var left = right.parent.Find(pair[0]) as RectTransform;
                        if (left == null || Mathf.Abs(left.anchoredPosition.y - right.anchoredPosition.y) > 1f
                            || left.anchoredPosition.x >= right.anchoredPosition.x) continue;
                        TMP_Text label = left.GetComponentInChildren<TMP_Text>(true);
                        if (label == null || label.font == null || string.IsNullOrEmpty(label.text)) continue;
                        string pt = Plugin.Translator.Translate(label.text);
                        if (pt == null) continue;
                        float grew = (TextFit.Width(label, pt) - TextFit.Width(label, label.text)) * label.fontSize
                                      * label.transform.lossyScale.x / Mathf.Max(1e-6f, right.parent.lossyScale.x);   // in the row's units
                        if (grew <= 0f) continue;
                        right.anchoredPosition += new Vector2(grew, 0f);
                    }
        }
    }
}
