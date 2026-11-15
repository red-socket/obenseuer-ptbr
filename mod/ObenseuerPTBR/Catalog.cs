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

        private readonly HashSet<string> values = new HashSet<string>(StringComparer.Ordinal);

        public int Count => byKey.Count + byText.Count;

        /// <summary>Entries keyed by English text (UI labels, code strings, templates).</summary>
        public IEnumerable<KeyValuePair<string, string>> TextEntries => byText;
        public int Fuzzy { get; private set; }

        public bool TryKey(string key, out string text) => byKey.TryGetValue(key, out text);

        public bool TryText(string english, out string text)
        {
            text = null;
            return english != null && byText.TryGetValue(english, out text);
        }

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
                        if (ctx != null) byKey[ctx] = str;
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
