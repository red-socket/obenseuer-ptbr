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
        private const int MaxDepth = 5;   // tags, trim, lines, separators and "Label:" can nest
        private const int CacheLimit = 8192;

        private static readonly Regex Placeholder = new Regex(@"\{(\d+)\}", RegexOptions.CultureInvariant);
        private static readonly Regex TranslationSlot = new Regex(@"\{(\d+)(?::([lu]))?\}", RegexOptions.CultureInvariant);
        private static readonly Regex Suffixed = new Regex(@"^([^()<>\n]+?) \(([^()<>\n]+)\)$", RegexOptions.CultureInvariant);
        private static readonly Regex TagSplit = new Regex(@"(<[^<>]+>)", RegexOptions.CultureInvariant);
        private static readonly Regex ParenGroups = new Regex(@"(?<=\)) (?=\()", RegexOptions.CultureInvariant);
        private static readonly Regex KeyHint = new Regex(@"^([^()<>]{1,16}\))([^()<>]+)$", RegexOptions.CultureInvariant);
        private static readonly Regex Labelled = new Regex(@"^([^:\n<>{}\[\]]{1,48}): (.+)$", RegexOptions.Singleline | RegexOptions.CultureInvariant);
        private static readonly Regex Counter = new Regex(@"^(.*\S) (\d+/\d+|[+-]\d+)$", RegexOptions.Singleline | RegexOptions.CultureInvariant);
        private static readonly string[] Separators = { " · ", " — " };
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

            // Objective counters and amounts: "Examine the apartments 3/17", "Theft +505".
            Match counter = Counter.Match(text);
            if (counter.Success)
            {
                string inner = Translate(counter.Groups[1].Value, depth + 1);
                if (inner != null) return inner + " " + counter.Groups[2].Value;
            }

            // Interaction verbs are drawn as "(Open)": translate the inside if the whole isn't known.
            if (text.Length > 2 && text[0] == '(' && text[text.Length - 1] == ')'
                && text.IndexOfAny(new[] { '(', ')', '<' }, 1, text.Length - 2) < 0)
            {
                string inner = Translate(text.Substring(1, text.Length - 2), depth + 1);
                if (inner != null) return "(" + inner + ")";
            }

            // Templates see the whole text first, final full stop included ("Threw away 3 items. Kept 1 stack: {0}.").
            foreach (Template t in templates)
            {
                Match m = t.Pattern.Match(text);
                if (!m.Success || CapturesTag(m)) continue;
                // {0} inserts the (translated) value; {0:l} / {0:u} lower-/upper-cases its first letter ("{1} com {0:l}").
                return TranslationSlot.Replace(t.Translation, p =>
                {
                    Group g = m.Groups["a" + p.Groups[1].Value];
                    if (!g.Success) return p.Value;
                    string v = Translate(g.Value, depth + 1) ?? List(g.Value, depth + 1) ?? g.Value;
                    if (!p.Groups[2].Success || v.Length == 0) return v;
                    char first = p.Groups[2].Value == "l" ? char.ToLower(v[0], PtBr) : char.ToUpper(v[0], PtBr);
                    return first + v.Substring(1);
                });
            }

            // Warnings and exclamations: "Thirst!" -> "Sede!". Single lines only: on a multi-line text, cutting the
            // final mark would leave its last line unmatched.
            char last = text[text.Length - 1];
            if (text.Length > 2 && (last == '!' || last == '?' || last == '.' || last == ':') && text.IndexOf('\n') < 0)
            {
                string inner = Translate(text.Substring(0, text.Length - 1), depth + 1);
                if (inner != null) return inner + last;
            }

            // "Log storage (Empty)": the name and the state are translated separately.
            Match suffixed = Suffixed.Match(text);
            if (suffixed.Success)
            {
                string a = Translate(suffixed.Groups[1].Value, depth + 1), b = Translate(suffixed.Groups[2].Value, depth + 1);
                if (a != null || b != null)
                {
                    if (b != null && b.Length > 0) b = char.ToLower(b[0], PtBr) + b.Substring(1);   // "(vazio)"
                    return (a ?? suffixed.Groups[1].Value) + " (" + (b ?? suffixed.Groups[2].Value) + ")";
                }
            }

            // Gamepad/keyboard hint line: "C)DRAG & DROP   R)DROP   Tab)EXIT".
            if (text.IndexOf(")", StringComparison.Ordinal) > 0)
            {
                string[] parts = text.Split(new[] { "   " }, StringSplitOptions.None);
                bool all = parts.Length > 0, changed = false;
                for (int i = 0; i < parts.Length && all; i++)
                {
                    Match k = KeyHint.Match(parts[i]);
                    if (!k.Success) { all = false; break; }
                    string tl = Translate(k.Groups[2].Value, depth + 1);
                    if (tl != null) { parts[i] = k.Groups[1].Value + tl; changed = true; }
                }
                if (all && changed) return string.Join("   ", parts);
            }

            // Several pieces in one label: rich-text runs ("<color>(Harvest)</color> <color>(Hold - Break)</color>")
            // or prompts side by side ("(LMB to plant) (Hold - Keep planting)"). Each piece is translated on its own.
            string[] pieces = text.IndexOf('<') >= 0 ? TagSplit.Split(text) : ParenGroups.Split(text);
            if (pieces.Length > 1)
            {
                bool changed = false;
                for (int i = 0; i < pieces.Length; i++)
                {
                    string piece = pieces[i];
                    if (piece.Length == 0 || piece[0] == '<' || piece.Trim().Length == 0) continue;
                    string tl = Translate(piece, depth + 1);
                    if (tl != null) { pieces[i] = tl; changed = true; }
                }
                if (changed) return string.Join(text.IndexOf('<') >= 0 ? "" : " ", pieces);
            }

            // Parts joined by a middle dot or a dash: "Next: Makeshift · Ken", "Bed — Pleasant, Safeish".
            if (text.IndexOf('\n') < 0)
                foreach (string sep in Separators)
                {
                    if (text.IndexOf(sep, StringComparison.Ordinal) <= 0) continue;
                    string[] parts = text.Split(new[] { sep }, StringSplitOptions.None);
                    bool changed = false;
                    for (int i = 0; i < parts.Length; i++)
                    {
                        string tl = Translate(parts[i], depth + 1) ?? List(parts[i], depth + 1);
                        if (tl != null) { parts[i] = tl; changed = true; }
                    }
                    if (changed) return string.Join(sep, parts);
                }

            // "Guard: Halt!" (bark and phone subtitles), "Quality: Good": translate a known label in front of
            // the colon, and the value too if it has a translation (dialogue values arrive already translated).
            // Single lines only: on a multi-line text the "value" would swallow the following lines.
            Match labelled = text.IndexOf('\n') < 0 ? Labelled.Match(text) : Match.Empty;
            if (labelled.Success)
            {
                string label = labelled.Groups[1].Value;
                string value = labelled.Groups[2].Value;
                string ptLabel = catalog.TryText(label, out string l) ? l
                    : catalog.TryTextIgnoreCase(label, out l) ? MatchCase(label, l) : null;
                string ptValue = Translate(value, depth + 1);
                if (ptLabel != null || ptValue != null)
                    return (ptLabel ?? label) + ": " + (ptValue ?? value);
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

        // A slot that swallowed rich-text tags or a "Label: " means the template matched across separate pieces of
        // a label ("{0} day" against "Sleeping: One day").
        private static bool CapturesTag(Match m)
        {
            for (int i = 1; i < m.Groups.Count; i++)
                if (m.Groups[i].Success && (m.Groups[i].Value.IndexOf('<') >= 0 || m.Groups[i].Value.IndexOf(": ", StringComparison.Ordinal) >= 0))
                    return true;
            return false;
        }

        // "Pleasant, Safeish": a comma list where every item is a known word. Later items start lower-case.
        private string List(string text, int depth)
        {
            if (text.IndexOf(", ", StringComparison.Ordinal) < 0) return null;
            string[] items = text.Split(new[] { ", " }, StringSplitOptions.None);
            for (int i = 0; i < items.Length; i++)
            {
                string tl = Translate(items[i], depth);
                if (tl == null || tl.Length == 0) return null;
                items[i] = i == 0 ? tl : char.ToLower(tl[0], PtBr) + tl.Substring(1);
            }
            return string.Join(", ", items);
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
            if (hasLower && !hasUpper) return pt.ToLower(PtBr);
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
                Pattern = new Regex(sb.ToString(), RegexOptions.CultureInvariant),   // "." stops at line breaks
                Translation = translation,
                Literal = literal,
            };
        }
    }
}
