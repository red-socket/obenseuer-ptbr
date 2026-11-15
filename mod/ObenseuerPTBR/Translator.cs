using System;
using System.Collections.Generic;
using System.Text;
using System.Text.RegularExpressions;

namespace ObenseuerPTBR
{
    /// <summary>
    /// Turns an English on-screen string into Portuguese, trying in order: exact match, trimmed match,
    /// match inside outer rich-text tags, templates ("Fill a Tank With {0}"), and line by line for
    /// multi-line labels. Returns null when nothing matched.
    /// </summary>
    internal sealed class Translator
    {
        private const int MaxDepth = 3;
        private const int CacheLimit = 8192;

        private static readonly Regex Placeholder = new Regex(@"\{(\d+)\}", RegexOptions.CultureInvariant);
        private static readonly Regex Counter = new Regex(@"^(.*\S) (\d+/\d+)$", RegexOptions.Singleline | RegexOptions.CultureInvariant);
        private static readonly System.Globalization.CultureInfo PtBr = new System.Globalization.CultureInfo("pt-BR");
        private static readonly Regex OuterTags = new Regex(@"^((?:<[^<>]+>)+)(.*?)((?:</?[^<>]+>)*)$",
            RegexOptions.Singleline | RegexOptions.CultureInvariant);

        private readonly Catalog catalog;
        private readonly List<Template> templates = new List<Template>();
        private readonly Dictionary<string, string> cache = new Dictionary<string, string>(StringComparer.Ordinal);

        private sealed class Template
        {
            public Regex Pattern;
            public string Translation;
            public int Literal;   // literal characters in the English, to try the most specific first
        }

        public Translator(Catalog catalog, Action<string> warn = null)
        {
            this.catalog = catalog;
            foreach (KeyValuePair<string, string> e in catalog.TextEntries)
            {
                if (!Placeholder.IsMatch(e.Key) || e.Key == e.Value) continue;   // identical: nothing to translate
                try { templates.Add(Compile(e.Key, e.Value)); }
                catch (ArgumentException ex) { warn?.Invoke($"Template \"{e.Key}\" skipped: {ex.Message}"); }
            }
            templates.Sort((a, b) => b.Literal.CompareTo(a.Literal));
        }

        public int TemplateCount => templates.Count;

        /// <summary>Portuguese for <paramref name="text"/>, or null if it has no translation.</summary>
        public string Translate(string text)
        {
            if (string.IsNullOrEmpty(text)) return null;
            if (cache.TryGetValue(text, out string cached)) return cached;
            string result = Translate(text, 0);
            if (cache.Count >= CacheLimit) cache.Clear();
            cache[text] = result;
            return result;
        }

        private string Translate(string text, int depth)
        {
            if (catalog.TryText(text, out string pt)) return pt;
            if (depth > MaxDepth) return null;

            string trimmed = text.Trim();
            if (trimmed.Length == 0) return null;
            if (trimmed.Length != text.Length)
            {
                string inner = Translate(trimmed, depth + 1);
                return inner == null ? null : text.Replace(trimmed, inner);
            }

            Match tags = OuterTags.Match(text);
            if (tags.Success && tags.Groups[2].Length > 0 && tags.Groups[2].Length < text.Length)
            {
                string inner = Translate(tags.Groups[2].Value, depth + 1);
                if (inner != null) return tags.Groups[1].Value + inner + tags.Groups[3].Value;
            }

            // Same text in other letter case: the game lower-cases names inside sentences and capitalizes labels.
            if (catalog.TryTextIgnoreCase(text, out pt)) return MatchCase(text, pt);

            // Objective counters: "Examine the apartments 3/17".
            Match counter = Counter.Match(text);
            if (counter.Success)
            {
                string inner = Translate(counter.Groups[1].Value, depth + 1);
                if (inner != null) return inner + " " + counter.Groups[2].Value;
            }

            // Interaction verbs are drawn as "(Open)": translate the inside if the whole isn't known.
            if (text.Length > 2 && text[0] == '(' && text[text.Length - 1] == ')')
            {
                string inner = Translate(text.Substring(1, text.Length - 2), depth + 1);
                if (inner != null) return "(" + inner + ")";
            }

            foreach (Template t in templates)
            {
                Match m = t.Pattern.Match(text);
                if (!m.Success) continue;
                return Placeholder.Replace(t.Translation, p =>
                {
                    Group g = m.Groups["a" + p.Groups[1].Value];
                    if (!g.Success) return p.Value;
                    return Translate(g.Value, depth + 1) ?? g.Value;
                });
            }

            if (text.IndexOf('\n') >= 0)
            {
                string[] lines = text.Split('\n');
                bool changed = false;
                for (int i = 0; i < lines.Length; i++)
                {
                    string line = lines[i].TrimEnd('\r');
                    if (line.Length == 0) continue;
                    string tl = Translate(line, depth + 1);
                    if (tl != null) { lines[i] = tl; changed = true; }
                }
                if (changed) return string.Join("\n", lines);
            }
            return null;
        }

        private static string MatchCase(string english, string pt)
        {
            bool hasLower = false, hasUpper = false;
            foreach (char c in english)
            {
                if (char.IsLower(c)) hasLower = true;
                else if (char.IsUpper(c)) hasUpper = true;
            }
            if (hasUpper && !hasLower) return pt.ToUpper(PtBr);
            if (english.Length > 0 && char.IsLower(english[0]) && pt.Length > 0)
                return char.ToLower(pt[0], PtBr) + pt.Substring(1);
            return pt;
        }

        // "Items added ({0})!" -> ^Items\ added\ \((?<a0>.+?)\)!$ ; a repeated {n} must match the same text.
        private static Template Compile(string english, string translation)
        {
            var sb = new StringBuilder("^");
            var seen = new HashSet<string>();
            int last = 0, literal = 0;
            foreach (Match p in Placeholder.Matches(english))
            {
                string lit = english.Substring(last, p.Index - last);
                sb.Append(Regex.Escape(lit));
                literal += lit.Length;
                string name = "a" + p.Groups[1].Value;
                sb.Append(seen.Add(name) ? $"(?<{name}>.+?)" : $"\\k<{name}>");
                last = p.Index + p.Length;
            }
            string tail = english.Substring(last);
            sb.Append(Regex.Escape(tail)).Append('$');
            literal += tail.Length;
            int letters = 0;
            foreach (char c in Placeholder.Replace(english, "")) if (char.IsLetter(c)) letters++;
            if (letters < 3)
                throw new ArgumentException("too little literal text to match safely");
            return new Template
            {
                Pattern = new Regex(sb.ToString(), RegexOptions.Singleline | RegexOptions.CultureInvariant),
                Translation = translation,
                Literal = literal,
            };
        }
    }
}
