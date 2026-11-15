using System.Collections.Generic;
using System.Text.RegularExpressions;
using HarmonyLib;
using PixelCrushers.DialogueSystem;

namespace ObenseuerPTBR
{
    /// <summary>
    /// Dialogue through the Dialogue System's own localization: every database the game loads gets a
    /// "&lt;lang&gt;" field (line text) and a "Menu Text &lt;lang&gt;" field (response button) per entry, in memory,
    /// and the Dialogue System's language is set to the plugin's language. Lines without a translation fall
    /// back to the English field. Conversation titles, Lua and variables are never touched.
    /// </summary>
    internal static class DialogueText
    {
        private static readonly HashSet<DialogueDatabase> done = new HashSet<DialogueDatabase>();

        public static void Localize(DialogueDatabase db)
        {
            Catalog cat = Plugin.Catalog;
            if (db == null || cat == null || !Plugin.Enabled.Value || !done.Add(db) || db.conversations == null) return;
            string lang = Plugin.Language.Value, menuField = "Menu Text " + lang;
            int lines = 0;
            foreach (Conversation conv in db.conversations)
            {
                if (conv?.dialogueEntries == null) continue;
                foreach (DialogueEntry entry in conv.dialogueEntries)
                {
                    if (entry?.fields == null) continue;
                    string key = $"dlg.{conv.id}.{entry.id}.";
                    if (cat.TryKey(key + "text", out string text)) { Set(entry.fields, lang, text); lines++; }
                    if (cat.TryKey(key + "menu", out string menu)) Set(entry.fields, menuField, menu);
                }
            }
            Plugin.Log.LogInfo($"Dialogue database {db.name}: {lines} lines translated");
        }

        private static void Set(List<Field> fields, string title, string value)
        {
            Field f = Field.Lookup(fields, title);
            if (f == null) fields.Add(new Field(title, value, FieldType.Localization));
            else f.value = value;
        }

        /// <summary>Switches the Dialogue System to the plugin's language (static, so once per scene is plenty).</summary>
        public static void ApplyLanguage(DialogueSystemController controller)
        {
            if (!Plugin.Enabled.Value) return;
            string lang = Plugin.Language.Value;
            Localization.language = lang;
            if (controller?.displaySettings?.localizationSettings != null)
                controller.displaySettings.localizationSettings.language = lang;
        }
    }

    [HarmonyPatch(typeof(DatabaseManager), nameof(DatabaseManager.Add))]
    internal static class DialogueDatabaseAddPatch
    {
        private static void Prefix(DialogueDatabase database) => DialogueText.Localize(database);
    }

    [HarmonyPatch(typeof(DialogueSystemController), nameof(DialogueSystemController.InitializeLocalization))]
    internal static class DialogueLanguagePatch
    {
        private static void Postfix(DialogueSystemController __instance) => DialogueText.ApplyLanguage(__instance);
    }

    /// <summary>
    /// Forms that depend on the player character's gender, written in translations as {{masculine|feminine}}
    /// ("Você está {{cansado|cansada}}?"). Resolved on screen from the dialogue variable PlayerGender.
    /// </summary>
    internal static class GenderMarkers
    {
        private static readonly Regex Marker = new Regex(@"\{\{([^{}|]*)\|([^{}|]*)\}\}", RegexOptions.CultureInvariant);

        public static string Resolve(string text)
        {
            if (text == null || text.IndexOf("{{", System.StringComparison.Ordinal) < 0) return text;
            bool female = false;
            try { female = DialogueLua.GetVariable("PlayerGender").asString == "female"; }
            catch (System.Exception) { }
            return Marker.Replace(text, m => female ? m.Groups[2].Value : m.Groups[1].Value);
        }
    }
}

namespace ObenseuerPTBR
{
    /// <summary>
    /// Words the game inserts into dialogue through Lua actor fields ([lua(Actor["Player"].AgeName)]):
    /// "boy", "young lady", "sir", "he"... set in English from the player's age and gender every time the
    /// identity is applied (each load). Overwritten right after, from manual.po keys player.&lt;Field&gt;.&lt;english&gt;.
    /// </summary>
    [HarmonyLib.HarmonyPatch(typeof(PlayerIdentity), nameof(PlayerIdentity.GetIdentity))]
    internal static class PlayerIdentityWordsPatch
    {
        private static readonly string[] Fields = { "AgeName", "AgeNameFormal", "AgeNameFormalShort", "Pronoun", "PronounCapitalized" };

        private static void Postfix()
        {
            if (!Plugin.Enabled.Value || Plugin.Catalog == null) return;
            foreach (string field in Fields)
            {
                string english = PixelCrushers.DialogueSystem.DialogueLua.GetActorField("Player", field).asString;
                if (!string.IsNullOrEmpty(english) && Plugin.Catalog.TryKey($"player.{field}.{english}", out string pt))
                    PixelCrushers.DialogueSystem.DialogueLua.SetActorField("Player", field, pt);
            }
        }
    }
}
