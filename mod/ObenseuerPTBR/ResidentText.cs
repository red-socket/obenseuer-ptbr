using System;
using System.Text.RegularExpressions;
using HarmonyLib;

namespace ObenseuerPTBR
{
    /// <summary>
    /// The resident tooltip (building map, character panel) lists relationship and job as plain English words,
    /// which Portuguese inflects by gender: "Noivo" / "Noiva", "Professor" / "Professora". The tooltip itself
    /// says the gender ("Gender: Female"), so after the game builds it, those two values are swapped for the
    /// form in the catalog entry "npc.&lt;English&gt;" ("{{Noivo|Noiva}}"). The rest is translated on screen.
    /// </summary>
    [HarmonyPatch]
    internal static class ResidentTooltipPatch
    {
        private static readonly Regex Value = new Regex(@"^(Relationship|Job): (.+)$", RegexOptions.Multiline | RegexOptions.CultureInvariant);
        private static readonly Regex Marker = new Regex(@"\{\{([^{}|]*)\|([^{}|]*)\}\}", RegexOptions.CultureInvariant);

        private static System.Collections.Generic.IEnumerable<System.Reflection.MethodBase> TargetMethods()
        {
            yield return AccessTools.Method(typeof(ResidentImageUI), nameof(ResidentImageUI.UpdateInfo));
            yield return AccessTools.Method(typeof(ResidentImageUI), nameof(ResidentImageUI.UpdateInfoPlayer));
        }

        private static void Postfix(ResidentImageUI __instance)
        {
            if (!Plugin.Enabled.Value || Plugin.Catalog == null) return;
            try
            {
                ToolTipInfo tip = __instance.toolTipInfo;
                string details = tip?.toolTipInfoDetails;
                if (string.IsNullOrEmpty(details)) return;
                bool female = details.IndexOf("Gender: Female", StringComparison.Ordinal) >= 0;
                string changed = Value.Replace(details, m =>
                {
                    string english = m.Groups[2].Value.TrimEnd('\r');
                    if (!Plugin.Catalog.TryKey("npc." + english, out string pt)) return m.Value;
                    return m.Groups[1].Value + ": " + Marker.Replace(pt, g => female ? g.Groups[2].Value : g.Groups[1].Value);
                });
                if (!ReferenceEquals(changed, details) && changed != details)
                    tip.UpdateToolTipInfo(tip.toolTipInfoTitle, changed);
            }
            catch (Exception e)
            {
                Plugin.Log.LogWarning($"Resident tooltip not adjusted: {e.Message}");
            }
        }
    }
}
