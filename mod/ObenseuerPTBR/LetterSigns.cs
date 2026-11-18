using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace ObenseuerPTBR
{
    /// <summary>
    /// Signs built from the game's 3D letter models ("letters_002_e", "letters_002_x", ...) standing in a column, such
    /// as the vertical EXCHANGE sign in the tenement yard. A catalog entry keyed "sign.&lt;WORD&gt;" replaces the word:
    /// the old letters are hidden (cut out of the merged scene mesh when the level designer combined them) and the
    /// game's own letter models spell the translation, centred in the same column. Only A-Z exist as models, so the
    /// translation can't carry accents. Runs on every scene load, since the scene comes back fresh each time.
    /// </summary>
    internal static class LetterSigns
    {
        private const string Prefix = "letters_002_";
        private const string Marker = " (pt-BR)";

        public static void Apply()
        {
            if (!Plugin.Enabled.Value || !Plugin.TranslateTextures.Value || Plugin.Catalog == null) return;
            try
            {
                var letters = Resources.FindObjectsOfTypeAll<MeshFilter>()
                    .Where(f => f != null && f.gameObject.scene.IsValid() && f.transform.parent != null && Letter(f.sharedMesh) != '\0')
                    .ToList();
                // Each letter has two models, "letters_002_a" and "letters_002_a_0"; for A and O one of them is the
                // Finnish Ä / Ö. The plain letter is the one with the smaller box.
                var models = new Dictionary<char, Mesh>();
                foreach (Mesh m in Resources.FindObjectsOfTypeAll<Mesh>())
                {
                    char c = Letter(m);
                    if (c == '\0') continue;
                    if (!models.TryGetValue(c, out Mesh had) || Size(m) < Size(had)) models[c] = m;
                }

                // A column: letters under one parent that share x and z and stand one step apart in y.
                foreach (var column in letters.GroupBy(f => (f.transform.parent, Mathf.Round(f.transform.localPosition.x * 100f), Mathf.Round(f.transform.localPosition.z * 100f))))
                {
                    var cells = column.OrderByDescending(f => f.transform.localPosition.y).ToList();
                    if (cells.Count < 3) continue;
                    string word = new string(cells.Select(f => Letter(f.sharedMesh)).ToArray());
                    if (!Plugin.Catalog.TryKey("sign." + word, out string pt)) continue;
                    Replace(cells, pt.ToUpperInvariant(), models, word);
                }
            }
            catch (Exception e)
            {
                Plugin.Log.LogWarning($"Letter signs not translated: {e.Message}");
            }
        }

        private static void Replace(List<MeshFilter> cells, string word, Dictionary<char, Mesh> models, string english)
        {
            Transform parent = cells[0].transform.parent;
            if (parent.Find(Prefix + word + Marker) != null) return;   // already done for this scene load
            if (word.Length > cells.Count || word.Any(c => !models.ContainsKey(c)))
            {
                Plugin.Log.LogWarning($"Letter sign {english}: \"{word}\" needs letters the game has no model for, or is longer; kept");
                return;
            }

            // Hide the old letters: switched-off letters live on in the parent's merged mesh, so cut them out of a copy.
            var boxes = new List<Bounds>();
            foreach (MeshFilter f in cells)
            {
                if (f.gameObject.activeInHierarchy) { var r = f.GetComponent<Renderer>(); if (r != null) r.enabled = false; }
                else boxes.Add(LocalBounds(f));
            }
            if (boxes.Count > 0)
            {
                // One box over the whole column, half a letter longer at each end, so no piece of an old letter is left.
                Bounds column = boxes[0];
                foreach (Bounds b in boxes) column.Encapsulate(b);
                Vector3 pad = (cells[1].transform.localPosition - cells[0].transform.localPosition) * 0.5f;
                column.Encapsulate(column.center + (column.extents.y + Mathf.Abs(pad.y)) * Vector3.up);
                column.Encapsulate(column.center - (column.extents.y + Mathf.Abs(pad.y)) * Vector3.up);
                if (!CutFromMerged(parent, new List<Bounds> { column }, cells[0].GetComponent<Renderer>()?.sharedMaterials)) return;
            }

            // Spell the new word with the same spacing, centred on the old column.
            Vector3 top = cells[0].transform.localPosition, step = cells[1].transform.localPosition - top;
            float offset = (cells.Count - word.Length) / 2f;
            Material[] materials = cells[0].GetComponent<Renderer>()?.sharedMaterials;
            var root = new GameObject(Prefix + word + Marker);
            root.transform.SetParent(parent, false);
            for (int i = 0; i < word.Length; i++)
            {
                var go = new GameObject(Prefix + char.ToLowerInvariant(word[i]));
                go.transform.SetParent(root.transform, false);
                go.transform.localPosition = top + step * (i + offset);
                go.transform.localRotation = cells[0].transform.localRotation;
                go.transform.localScale = cells[0].transform.localScale;
                go.AddComponent<MeshFilter>().sharedMesh = models[word[i]];
                go.AddComponent<MeshRenderer>().sharedMaterials = materials;
            }
            Plugin.Log.LogInfo($"Letter sign {english} -> {word}");
        }

        /// <summary>Removes, from the parent's merged mesh, the triangles of the given materials inside the boxes.</summary>
        private static bool CutFromMerged(Transform parent, List<Bounds> boxes, Material[] letterMaterials)
        {
            var filter = parent.GetComponent<MeshFilter>();
            var renderer = parent.GetComponent<MeshRenderer>();
            if (filter == null || renderer == null || filter.sharedMesh == null || !filter.sharedMesh.isReadable) return false;
            var names = new HashSet<string>((letterMaterials ?? new Material[0]).Where(m => m != null).Select(m => m.name));
            Mesh mesh = UnityEngine.Object.Instantiate(filter.sharedMesh);
            mesh.name = filter.sharedMesh.name + Marker;
            Vector3[] v = mesh.vertices;
            Material[] mats = renderer.sharedMaterials;
            int cut = 0;
            for (int s = 0; s < mesh.subMeshCount && s < mats.Length; s++)
            {
                if (mats[s] == null || !names.Contains(mats[s].name)) continue;
                int[] tris = mesh.GetTriangles(s);
                var keep = new List<int>(tris.Length);
                for (int t = 0; t < tris.Length; t += 3)
                {
                    Vector3 c = (v[tris[t]] + v[tris[t + 1]] + v[tris[t + 2]]) / 3f;
                    if (boxes.Any(b => b.Contains(c))) { cut++; continue; }
                    keep.Add(tris[t]); keep.Add(tris[t + 1]); keep.Add(tris[t + 2]);
                }
                mesh.SetTriangles(keep, s);
            }
            filter.sharedMesh = mesh;
            return cut > 0;
        }

        private static float Size(Mesh m) { Vector3 e = m.bounds.extents; return e.x + e.y + e.z; }

        // The letter's model bounds in its parent's space (the space the merged mesh is in), a little enlarged.
        private static Bounds LocalBounds(MeshFilter f)
        {
            Bounds b = f.sharedMesh.bounds;
            Matrix4x4 m = Matrix4x4.TRS(f.transform.localPosition, f.transform.localRotation, f.transform.localScale);
            var result = new Bounds(m.MultiplyPoint3x4(b.center), Vector3.zero);
            for (int i = 0; i < 8; i++)
            {
                Vector3 corner = b.center + Vector3.Scale(b.extents, new Vector3((i & 1) == 0 ? -1 : 1, (i & 2) == 0 ? -1 : 1, (i & 4) == 0 ? -1 : 1));
                result.Encapsulate(m.MultiplyPoint3x4(corner));
            }
            result.Expand(0.01f);
            return result;
        }

        // 'E' for "letters_002_e", "letters_002_e_0"; '\0' for anything else (arrows, dashes, dots).
        private static char Letter(Mesh mesh)
        {
            if (mesh == null || !mesh.name.StartsWith(Prefix, StringComparison.Ordinal) || mesh.name.Length <= Prefix.Length) return '\0';
            string rest = mesh.name.Substring(Prefix.Length);
            if (rest.Length != 1 && !(rest.Length == 3 && rest.EndsWith("_0", StringComparison.Ordinal))) return '\0';
            char c = char.ToUpperInvariant(rest[0]);
            return c >= 'A' && c <= 'Z' ? c : '\0';
        }
    }
}
