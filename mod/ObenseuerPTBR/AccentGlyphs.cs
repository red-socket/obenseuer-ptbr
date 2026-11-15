using System;
using System.Collections.Generic;
using TMPro;
using UnityEngine;
using UnityEngine.TextCore;

namespace ObenseuerPTBR
{
    /// <summary>
    /// The typewriter font (Erika Ormig) has broken accented letters: its tildes are blobs and the accents on
    /// capitals sit on top of the letter. Its font assets are static SDF atlases, so the broken glyphs are
    /// redrawn in place once per atlas, in memory: the base letter and accent are taken from the same atlas
    /// (the tilde, which the font lacks, is drawn as a sine stroke), and the glyph metrics are widened to fit.
    /// Nothing is written to disk, and each glyph keeps its atlas slot, so the text itself is unchanged.
    /// </summary>
    internal static class AccentGlyphs
    {
        private const string FontPrefix = "Erika Ormig";
        private const float Em = 65.078125f;     // glyph advance at the 108 pt sampling size; other sizes scale by this
        private const float CapitalLift = 18f;   // how far accents rise over capitals, in 108 pt units

        // Accented letter -> base letter and accent ('~' is drawn, the others come from the font).
        private static readonly string[] Targets =
        {
            "ãa~", "õo~", "âa^", "êe^", "ôo^",
            "ÃA~", "ÕO~", "ÂA^", "ÊE^", "ÔO^", "ÁA´", "ÀA`", "ÉE´", "ÍI´", "ÓO´", "ÚU´",
        };

        private static readonly HashSet<TMP_FontAsset> doneFonts = new HashSet<TMP_FontAsset>();
        // Metrics of the redrawn glyphs per atlas, for another font asset that shares the same atlas.
        private static readonly Dictionary<Texture, Dictionary<uint, GlyphMetrics>> doneAtlases =
            new Dictionary<Texture, Dictionary<uint, GlyphMetrics>>();

        public static void FixAll()
        {
            if (!Plugin.Enabled.Value || !Plugin.FixFontAccents.Value) return;
            foreach (TMP_FontAsset font in Resources.FindObjectsOfTypeAll<TMP_FontAsset>())
            {
                if (font == null || !font.name.StartsWith(FontPrefix, StringComparison.Ordinal) || !doneFonts.Add(font)) continue;
                try { Fix(font); }
                catch (Exception e) { Plugin.Log.LogWarning($"Font {font.name}: accents not redrawn: {e.Message}"); }
            }
        }

        private sealed class Atlas
        {
            public int W, H, Pad;
            public float[] A;   // SDF values 0..1, row 0 at the bottom (TMP glyph rects count from the bottom)

            public float At(int x, int y) => x < 0 || y < 0 || x >= W || y >= H ? 0f : A[y * W + x];
        }

        private static void Fix(TMP_FontAsset font)
        {
            Texture2D tex = font.atlasTexture;
            if (font.atlasPopulationMode != AtlasPopulationMode.Static || tex == null || tex.format != TextureFormat.Alpha8)
                return;
            var lookup = font.characterLookupTable;
            if (doneAtlases.TryGetValue(tex, out var known))
            {
                foreach (var e in known)
                    if (lookup.TryGetValue(e.Key, out TMP_Character c)) c.glyph.metrics = e.Value;
                TMPro_EventManager.ON_FONT_PROPERTY_CHANGED(true, font);
                return;
            }
            Glyph G(char c) => lookup.TryGetValue(c, out TMP_Character ch) ? ch.glyph : null;
            Glyph a = G('a');
            if (a == null) return;
            float k = a.metrics.horizontalAdvance / Em;

            var atlas = new Atlas { W = tex.width, H = tex.height, Pad = font.atlasPadding, A = Read(tex) };
            if (!BottomUp(atlas, font)) Flip(atlas);
            float spread = font.atlasPadding + 1;   // _GradientScale of TMP SDF materials

            var redrawn = new Dictionary<uint, GlyphMetrics>();
            foreach (string t in Targets)
            {
                Glyph target = G(t[0]), b = G(t[1]);
                if (target == null || b == null) continue;
                float lift = char.IsUpper(t[1]) ? CapitalLift * k : 0f;
                Func<float, float, float> accent;
                Rect box;
                if (t[2] == '~')
                {
                    Glyph acute = G('´');
                    if (acute == null) continue;
                    float top = acute.metrics.horizontalBearingY + lift;
                    float cx = b.metrics.horizontalAdvance / 2f, cy = top - acute.metrics.height / 2f - 2f * k;
                    float half = 17f * k, amp = 4.5f * k, thick = 9.5f * k;
                    box = Rect.MinMaxRect(cx - half - thick, cy - amp - thick, cx + half + thick, cy + amp + thick);
                    accent = (x, y) => Tilde(x, y, cx, cy, half, amp, thick, spread);
                }
                else
                {
                    Glyph g = G(t[2]);
                    if (g == null) continue;
                    GlyphMetrics m = g.metrics;
                    box = Rect.MinMaxRect(m.horizontalBearingX, m.horizontalBearingY - m.height + lift,
                                          m.horizontalBearingX + m.width, m.horizontalBearingY + lift);
                    accent = (x, y) => Sample(atlas, g, x, y - lift);
                }
                Compose(atlas, target, b, accent, box);
                redrawn[t[0]] = target.metrics;
            }
            if (redrawn.Count == 0) return;
            Write(tex, font, atlas);
            doneAtlases[tex] = redrawn;
            TMPro_EventManager.ON_FONT_PROPERTY_CHANGED(true, font);
            Plugin.Log.LogInfo($"Font {font.name}: redrew {redrawn.Count} accented letters");
        }

        // Draws base + accent into the target glyph's atlas slot, scaled to fit it, and sets the target's metrics
        // to the combined box so TMP stretches the slot back to the right size.
        private static void Compose(Atlas atlas, Glyph target, Glyph b, Func<float, float, float> accent, Rect box)
        {
            GlyphMetrics bm = b.metrics;
            float x0 = Mathf.Min(bm.horizontalBearingX, box.xMin), x1 = Mathf.Max(bm.horizontalBearingX + bm.width, box.xMax);
            float y0 = Mathf.Min(bm.horizontalBearingY - bm.height, box.yMin), y1 = Mathf.Max(bm.horizontalBearingY, box.yMax);
            GlyphRect r = target.glyphRect;
            float sx = r.width / (x1 - x0), sy = r.height / (y1 - y0);
            int pad = atlas.Pad;
            var patch = new float[(r.width + 2 * pad) * (r.height + 2 * pad)];
            int i = 0;
            for (int v = r.y - pad; v < r.y + r.height + pad; v++)
                for (int u = r.x - pad; u < r.x + r.width + pad; u++)
                {
                    float x = x0 + (u + 0.5f - r.x) / sx, y = y0 + (v + 0.5f - r.y) / sy;
                    patch[i++] = Mathf.Max(Sample(atlas, b, x, y), accent(x, y));
                }
            i = 0;
            for (int v = r.y - pad; v < r.y + r.height + pad; v++)
                for (int u = r.x - pad; u < r.x + r.width + pad; u++, i++)
                    if (u >= 0 && v >= 0 && u < atlas.W && v < atlas.H) atlas.A[v * atlas.W + u] = patch[i];
            target.metrics = new GlyphMetrics(x1 - x0, y1 - y0, x0, y1, target.metrics.horizontalAdvance);
        }

        // SDF value of glyph g at a point in font units (y up from the baseline); 0 outside its padded slot.
        private static float Sample(Atlas atlas, Glyph g, float x, float y)
        {
            GlyphMetrics m = g.metrics;
            GlyphRect r = g.glyphRect;
            if (m.width <= 0f || m.height <= 0f) return 0f;
            float ax = r.x + (x - m.horizontalBearingX) * r.width / m.width - 0.5f;
            float ay = r.y + (y - (m.horizontalBearingY - m.height)) * r.height / m.height - 0.5f;
            int ix = Mathf.FloorToInt(ax), iy = Mathf.FloorToInt(ay);
            float fx = ax - ix, fy = ay - iy;
            float In(int px, int py) =>
                px < r.x - atlas.Pad || py < r.y - atlas.Pad || px >= r.x + r.width + atlas.Pad || py >= r.y + r.height + atlas.Pad
                    ? 0f : atlas.At(px, py);
            return In(ix, iy) * (1 - fx) * (1 - fy) + In(ix + 1, iy) * fx * (1 - fy)
                 + In(ix, iy + 1) * (1 - fx) * fy + In(ix + 1, iy + 1) * fx * fy;
        }

        // SDF of a tilde: one period of a sine wave, drawn as a stroke of the given thickness.
        private static float Tilde(float x, float y, float cx, float cy, float half, float amp, float thick, float spread)
        {
            if (x < cx - half - thick * 2 || x > cx + half + thick * 2 || y < cy - amp - thick * 2 || y > cy + amp + thick * 2)
                return 0f;
            float best = float.MaxValue;
            const int Steps = 64;
            for (int s = 0; s <= Steps; s++)
            {
                float t = -1f + 2f * s / Steps;
                float dx = x - (cx + t * half), dy = y - (cy + amp * Mathf.Sin(t * Mathf.PI));
                best = Mathf.Min(best, dx * dx + dy * dy);
            }
            float d = Mathf.Sqrt(best) - thick / 2f;
            return Mathf.Clamp01(0.5f - d / (2f * spread));
        }

        private static float[] Read(Texture2D tex)
        {
            RenderTexture rt = RenderTexture.GetTemporary(tex.width, tex.height, 0, RenderTextureFormat.ARGB32, RenderTextureReadWrite.Linear);
            RenderTexture prev = RenderTexture.active;
            var copy = new Texture2D(tex.width, tex.height, TextureFormat.RGBA32, false, true);
            try
            {
                Graphics.Blit(tex, rt);
                RenderTexture.active = rt;
                copy.ReadPixels(new Rect(0, 0, tex.width, tex.height), 0, 0, false);
                copy.Apply(false);
            }
            finally
            {
                RenderTexture.active = prev;
                RenderTexture.ReleaseTemporary(rt);
            }
            Color32[] px = copy.GetPixels32();
            UnityEngine.Object.Destroy(copy);
            // Alpha8 normally samples as (0, 0, 0, a); if alpha came back solid, the value is in red.
            bool alphaSolid = true;
            for (int i = 0; i < px.Length && alphaSolid; i += 97) alphaSolid = px[i].a == 255;
            var a = new float[px.Length];
            for (int i = 0; i < px.Length; i++) a[i] = (alphaSolid ? px[i].r : px[i].a) / 255f;
            return a;
        }

        // Glyph slots must hold ink: check a few letters, in case the read-back came out upside down.
        private static bool BottomUp(Atlas atlas, TMP_FontAsset font)
        {
            float up = 0f, down = 0f;
            foreach (char c in "aemoBHMW")
            {
                if (!font.characterLookupTable.TryGetValue(c, out TMP_Character ch)) continue;
                GlyphRect r = ch.glyph.glyphRect;
                for (int y = r.y; y < r.y + r.height; y += 2)
                    for (int x = r.x; x < r.x + r.width; x += 2)
                    {
                        up += atlas.At(x, y);
                        down += atlas.At(x, atlas.H - 1 - y);
                    }
            }
            return up >= down;
        }

        private static void Flip(Atlas atlas)
        {
            for (int y = 0; y < atlas.H / 2; y++)
                for (int x = 0; x < atlas.W; x++)
                {
                    int i = y * atlas.W + x, j = (atlas.H - 1 - y) * atlas.W + x;
                    float t = atlas.A[i]; atlas.A[i] = atlas.A[j]; atlas.A[j] = t;
                }
        }

        private static void Write(Texture2D tex, TMP_FontAsset font, Atlas atlas)
        {
            var bytes = new byte[atlas.A.Length];
            for (int i = 0; i < bytes.Length; i++) bytes[i] = (byte)Mathf.RoundToInt(Mathf.Clamp01(atlas.A[i]) * 255f);
            var fixedTex = new Texture2D(tex.width, tex.height, TextureFormat.Alpha8, false, true)
            {
                name = tex.name, filterMode = tex.filterMode, wrapMode = tex.wrapMode, anisoLevel = tex.anisoLevel,
            };
            fixedTex.SetPixelData(bytes, 0);
            fixedTex.Apply(false, false);
            if (SystemInfo.copyTextureSupport != UnityEngine.Rendering.CopyTextureSupport.None)
            {
                // Same size and format: copy on the GPU, so every material keeps pointing at the game's texture.
                Graphics.CopyTexture(fixedTex, tex);
                UnityEngine.Object.Destroy(fixedTex);
                return;
            }
            font.atlasTextures[0] = fixedTex;
            foreach (Material m in Resources.FindObjectsOfTypeAll<Material>())
                if (m != null && m.HasProperty(ShaderUtilities.ID_MainTex) && m.GetTexture(ShaderUtilities.ID_MainTex) == tex)
                    m.SetTexture(ShaderUtilities.ID_MainTex, fixedTex);
        }
    }
}
