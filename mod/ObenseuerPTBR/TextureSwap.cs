using System.Collections;
using System.Collections.Generic;
using System.IO;
using UnityEngine;

namespace ObenseuerPTBR
{
    /// <summary>
    /// Textures with text (signs, posters, packaging): a PNG in textures/&lt;lang&gt;/ named like the game texture
    /// replaces that texture's pixels in memory when it is loaded. Only same-size textures are replaced, so
    /// sprites and UV layouts stay valid. Game files are never touched.
    /// </summary>
    internal static class TextureSwap
    {
        private static readonly Dictionary<string, string> files = new Dictionary<string, string>(System.StringComparer.Ordinal);
        private static readonly Dictionary<string, byte[]> bytes = new Dictionary<string, byte[]>(System.StringComparer.Ordinal);
        // A few pixels of each replaced texture, by instance ID. Unity reloads a scene's textures from disk under the
        // same instance ID when you come back through a door, so the ID alone can't tell a replaced texture from a
        // fresh copy of the original: the pixels can.
        private static readonly Dictionary<int, Color32[]> swapped = new Dictionary<int, Color32[]>();
        private static readonly HashSet<string> wrongSize = new HashSet<string>(System.StringComparer.Ordinal);

        // UnityEngine.ImageConversion.LoadImage(Texture2D, byte[], bool), looked up at runtime: the module is built
        // against netstandard 2.1 and can't be referenced from this net472 project.
        private static readonly System.Reflection.MethodInfo LoadImageMethod =
            System.Type.GetType("UnityEngine.ImageConversion, UnityEngine.ImageConversionModule")
                ?.GetMethod("LoadImage", new[] { typeof(Texture2D), typeof(byte[]), typeof(bool) });

        private static bool LoadImage(Texture2D tex, byte[] data) =>
            LoadImageMethod != null && (bool)LoadImageMethod.Invoke(null, new object[] { tex, data, false });

        public static void LoadFolder(string folder)
        {
            if (!Directory.Exists(folder)) return;
            foreach (string path in Directory.GetFiles(folder, "*.png", SearchOption.AllDirectories))
                files[Path.GetFileNameWithoutExtension(path)] = path;
            if (files.Count > 0) Plugin.Log.LogInfo($"{files.Count} replacement textures available");
        }

        public static int Count => files.Count;

        /// <summary>Replaces every loaded texture that has a translation and wasn't replaced yet.</summary>
        public static void Apply()
        {
            if (files.Count == 0 || !Plugin.TranslateTextures.Value || !Plugin.Enabled.Value) return;
            int n = 0;
            foreach (Texture2D tex in Resources.FindObjectsOfTypeAll<Texture2D>())
            {
                if (tex == null || !files.TryGetValue(tex.name, out string path) || wrongSize.Contains(tex.name) || StillReplaced(tex)) continue;
                swapped.Remove(tex.GetInstanceID());
                try
                {
                    if (!bytes.TryGetValue(tex.name, out byte[] data)) bytes[tex.name] = data = File.ReadAllBytes(path);
                    var probe = new Texture2D(2, 2);
                    if (!LoadImage(probe, data) || probe.width != tex.width || probe.height != tex.height)
                    {
                        Plugin.Log.LogWarning($"Texture {tex.name}: replacement is {probe.width}x{probe.height}, game texture is {tex.width}x{tex.height}; skipped");
                        wrongSize.Add(tex.name);
                        Object.Destroy(probe);
                        continue;
                    }
                    Object.Destroy(probe);
                    // LoadImage re-initialises the texture with the PNG's pixels; materials and sprites keep pointing at it.
                    // It also leaves the texture readable, which game textures normally are not.
                    LoadImage(tex, data);
                    swapped[tex.GetInstanceID()] = Sample(tex);
                    n++;
                }
                catch (System.Exception e)
                {
                    Plugin.Log.LogWarning($"Texture {tex.name} not replaced: {e.Message}");
                }
            }
            if (n > 0) Plugin.Log.LogInfo($"Replaced {n} textures");
        }

        private static bool StillReplaced(Texture2D tex)
        {
            if (!swapped.TryGetValue(tex.GetInstanceID(), out Color32[] sample) || !tex.isReadable) return false;
            Color32[] now = Sample(tex);
            for (int i = 0; i < sample.Length; i++)
                if (!sample[i].Equals(now[i])) return false;
            return true;
        }

        // Five pixels spread over the texture (corners and centre would often be plain background, so off-centre).
        private static Color32[] Sample(Texture2D tex)
        {
            int w = tex.width, h = tex.height;
            return new[]
            {
                (Color32)tex.GetPixel(w / 3, h / 3), (Color32)tex.GetPixel(2 * w / 3, h / 3), (Color32)tex.GetPixel(w / 2, h / 2),
                (Color32)tex.GetPixel(w / 3, 2 * h / 3), (Color32)tex.GetPixel(2 * w / 3, 2 * h / 3),
            };
        }

        /// <summary>Scene objects and Addressables can load their textures a little after the scene: look again.</summary>
        public static IEnumerator ApplyLater()
        {
            yield return new WaitForSecondsRealtime(3f);
            Apply();
        }
    }
}
