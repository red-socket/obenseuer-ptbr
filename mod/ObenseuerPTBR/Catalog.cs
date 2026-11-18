using System;
using System.Collections.Generic;
using System.IO;
using System.Text;

namespace ObenseuerPTBR
{
    /// <summary>
    /// Translations loaded from gettext .po files. Entries with a msgctxt are looked up by that key
    /// (item.12.title, dlg.67.3.text, ...); entries without one are looked up by their English text.
    /// Untranslated entries are skipped, so every lookup falls back to the game's English.
    /// </summary>
    internal sealed class Catalog
    {
        private readonly Dictionary<string, string> byKey = new Dictionary<string, string>(StringComparer.Ordinal);
        private readonly Dictionary<string, string> byText = new Dictionary<string, string>(StringComparer.Ordinal);
        // Keyed entries (tasks, notes, furniture...) by their English text, for labels that show them verbatim.
        private readonly Dictionary<string, string> promoted = new Dictionary<string, string>(StringComparer.Ordinal);
        private Dictionary<string, string> folded;   // lower-cased English -> translation, built on first use

        private readonly HashSet<string> values = new HashSet<string>(StringComparer.Ordinal);

        public int Count => byKey.Count + byText.Count;

        /// <summary>Entries keyed by English text (UI labels, code strings, templates).</summary>
        public IEnumerable<KeyValuePair<string, string>> TextEntries => byText;
        public int Fuzzy { get; private set; }

        public bool TryKey(string key, out string text) => byKey.TryGetValue(key, out text);

        /// <summary>Keyed entries whose key starts with <paramref name="prefix"/>, by the rest of the key.</summary>
        public Dictionary<string, string> KeysWithPrefix(string prefix)
        {
            var map = new Dictionary<string, string>(StringComparer.Ordinal);
            foreach (var e in byKey)
                if (e.Key.StartsWith(prefix, StringComparison.Ordinal)) map[e.Key.Substring(prefix.Length)] = e.Value;
            return map;
        }

        public bool TryText(string english, out string text)
        {
            text = null;
            return english != null && (byText.TryGetValue(english, out text) || promoted.TryGetValue(english, out text));
        }

        /// <summary>Case-insensitive lookup ("heating room", "NEW GAME"); the caller restores the case.</summary>
        public bool TryTextIgnoreCase(string english, out string text)
        {
            if (folded == null)
            {
                folded = new Dictionary<string, string>(StringComparer.Ordinal);
                foreach (var e in promoted) folded[e.Key.ToLowerInvariant()] = e.Value;
                foreach (var e in byText) folded[e.Key.ToLowerInvariant()] = e.Value;
            }
            text = null;
            return english != null && folded.TryGetValue(english.ToLowerInvariant(), out text);
        }

        // Keyed entries that also apply wherever their English text is shown. Dialogue lines, player words,
        // context entries ("scope:<object>:<English>"), other mods' strings ("mod.<Mod>:<English>") and
        // gendered resident words ("npc.<English>"), the doctor's diagnosis pieces ("doctor.*") and 3D letter signs
        // ("sign.<WORD>") only apply to their own key.
        private static bool Promotable(string ctx) =>
            !ctx.StartsWith("dlg.", StringComparison.Ordinal) && !ctx.StartsWith("player.", StringComparison.Ordinal)
            && !ctx.StartsWith("scope:", StringComparison.Ordinal) && !ctx.StartsWith("mod.", StringComparison.Ordinal)
            && !ctx.StartsWith("npc.", StringComparison.Ordinal) && !ctx.StartsWith("doctor.", StringComparison.Ordinal)
            && !ctx.StartsWith("sign.", StringComparison.Ordinal);

        /// <summary>True if the text is already a translation (so it is not reported as untranslated).</summary>
        public bool IsTranslation(string text) => values.Contains(text);

        public void LoadFolder(string folder, bool useFuzzy)
        {
            if (!Directory.Exists(folder))
                return;
            foreach (string file in Directory.GetFiles(folder, "*.po", SearchOption.AllDirectories))
                Load(file, useFuzzy);
        }

        public void Load(string path, bool useFuzzy)
        {
            string ctx = null, id = null, str = null, field = null;
            bool fuzzy = false;
            var buf = new StringBuilder();

            void Flush()
            {
                if (field == "msgctxt") ctx = buf.ToString();
                else if (field == "msgid") id = buf.ToString();
                else if (field == "msgstr") str = buf.ToString();
                buf.Length = 0;
                field = null;
            }

            void Commit()
            {
                Flush();
                if (!string.IsNullOrEmpty(id) && !string.IsNullOrEmpty(str))
                {
                    if (fuzzy) Fuzzy++;
                    if (!fuzzy || useFuzzy)
                    {
                        if (ctx != null)
                        {
                            byKey[ctx] = str;
                            if (Promotable(ctx) && !promoted.ContainsKey(id))
                                promoted[id] = str;
                        }
                        else byText[id] = str;
                        values.Add(str);
                    }
                }
                ctx = id = str = null;
                fuzzy = false;
            }

            foreach (string raw in File.ReadAllLines(path, Encoding.UTF8))
            {
                string line = raw.Trim();
                if (line.Length == 0) { Commit(); continue; }
                if (line.StartsWith("#,")) { if (field == "msgstr") Commit(); fuzzy |= line.Contains("fuzzy"); continue; }
                if (line.StartsWith("#")) { if (field == "msgstr") Commit(); continue; }
                if (line.StartsWith("\"")) { buf.Append(Unescape(line)); continue; }

                int sp = line.IndexOf(' ');
                if (sp < 0) continue;
                string kw = line.Substring(0, sp);
                if (kw == "msgctxt" && field == "msgstr") Commit();
                if (kw == "msgid" && field == "msgstr") Commit();
                Flush();
                field = kw;
                buf.Append(Unescape(line.Substring(sp + 1).Trim()));
            }
            Commit();
        }

        private static string Unescape(string quoted)
        {
            if (quoted.Length < 2 || quoted[0] != '"' || quoted[quoted.Length - 1] != '"')
                return "";
            var sb = new StringBuilder(quoted.Length);
            for (int i = 1; i < quoted.Length - 1; i++)
            {
                char c = quoted[i];
                if (c != '\\' || i + 1 >= quoted.Length - 1) { sb.Append(c); continue; }
                char n = quoted[++i];
                switch (n)
                {
                    case 'n': sb.Append('\n'); break;
                    case 't': sb.Append('\t'); break;
                    case 'r': sb.Append('\r'); break;
                    default: sb.Append(n); break;
                }
            }
            return sb.ToString();
        }
    }
}
