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
        private static readonly HashSet<int> swapped = new HashSet<int>();

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
                if (tex == null || !files.TryGetValue(tex.name, out string path) || swapped.Contains(tex.GetInstanceID())) continue;
                swapped.Add(tex.GetInstanceID());
                try
                {
                    if (!bytes.TryGetValue(tex.name, out byte[] data)) bytes[tex.name] = data = File.ReadAllBytes(path);
                    var probe = new Texture2D(2, 2);
                    if (!LoadImage(probe, data) || probe.width != tex.width || probe.height != tex.height)
                    {
                        Plugin.Log.LogWarning($"Texture {tex.name}: replacement is {probe.width}x{probe.height}, game texture is {tex.width}x{tex.height}; skipped");
                        Object.Destroy(probe);
                        continue;
                    }
                    Object.Destroy(probe);
                    // LoadImage re-initialises the texture with the PNG's pixels; materials and sprites keep pointing at it.
                    LoadImage(tex, data);
                    n++;
                }
                catch (System.Exception e)
                {
                    Plugin.Log.LogWarning($"Texture {tex.name} not replaced: {e.Message}");
                }
            }
            if (n > 0) Plugin.Log.LogInfo($"Replaced {n} textures");
        }

        /// <summary>Scene objects and Addressables can load their textures a little after the scene: look again.</summary>
        public static IEnumerator ApplyLater()
        {
            yield return new WaitForSecondsRealtime(3f);
            Apply();
        }
    }
}
