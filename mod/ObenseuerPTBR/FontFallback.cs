using System.Collections.Generic;
using TMPro;
using UnityEngine;

namespace ObenseuerPTBR
{
    /// <summary>
    /// Makes sure every loaded TMP font can draw Portuguese accents. The game's main fonts already have them,
    /// and Chalkiez falls back to the dynamic NotoSans-Bold, so this is a safety net: a font that still lacks
    /// glyphs after searching its fallbacks gets a dynamic font that has them.
    /// </summary>
    internal static class FontFallback
    {
        private const string Accents = "áàâãçéêíóôõúüÁÀÂÃÇÉÊÍÓÔÕÚÜ";
        private static readonly string[] Donors = { "NotoSans-Bold SDF", "LiberationSans SDF - Fallback", "LiberationSans SDF" };
        private static readonly HashSet<TMP_FontAsset> checkedFonts = new HashSet<TMP_FontAsset>();

        public static void Check()
        {
            TMP_FontAsset[] fonts = Resources.FindObjectsOfTypeAll<TMP_FontAsset>();
            TMP_FontAsset donor = null;
            foreach (TMP_FontAsset font in fonts)
            {
                if (font == null || !checkedFonts.Add(font) || font.name.Contains("Icons")) continue;
                if (font.HasCharacters(Accents, out uint[] missing, true, true)) continue;

                donor = donor ?? FindDonor(fonts);
                if (donor == null || donor == font)
                {
                    Plugin.Log.LogWarning($"Font {font.name} cannot draw: {Chars(missing)}");
                    continue;
                }
                if (font.fallbackFontAssetTable == null) font.fallbackFontAssetTable = new List<TMP_FontAsset>();
                if (!font.fallbackFontAssetTable.Contains(donor)) font.fallbackFontAssetTable.Add(donor);
                Plugin.Log.LogInfo($"Font {font.name} lacked {Chars(missing)}; added {donor.name} as fallback");
            }
        }

        private static string Chars(uint[] codes)
        {
            var sb = new System.Text.StringBuilder();
            if (codes != null) foreach (uint c in codes) sb.Append((char)c);
            return sb.ToString();
        }

        private static TMP_FontAsset FindDonor(TMP_FontAsset[] fonts)
        {
            foreach (string name in Donors)
                foreach (TMP_FontAsset f in fonts)
                    if (f != null && f.name == name && f.HasCharacters(Accents, out _, false, true))
                        return f;
            return null;
        }
    }
}
