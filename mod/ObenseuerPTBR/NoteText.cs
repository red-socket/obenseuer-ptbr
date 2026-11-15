using HarmonyLib;

namespace ObenseuerPTBR
{
    /// <summary>
    /// The note viewer shows the open note through two input fields (title and text). The label hook doesn't
    /// reliably catch them, so the viewer's fields get the Portuguese directly after the game fills them.
    /// Notes the player can write in (notebooks) are left alone: what is in those fields gets saved.
    /// </summary>
    [HarmonyPatch(typeof(NotesPanel), "ShowNoteInfo")]
    internal static class NoteViewerPatch
    {
        private static void Postfix(NotesPanel __instance, int index)
        {
            if (!Plugin.Enabled.Value || Plugin.Translator == null) return;
            try
            {
                NoteUIPanel panel = __instance.noteList[index].GetComponent<NoteUIPanel>();
                CollectedNoteInfo note = panel?.note;
                if (note == null || note.canEdit || note.writable != null) return;
                NoteInfo page = note.CurrentPage;
                string title = Translate(page.title), content = Translate(page.content);
                if (title != null)
                {
                    __instance.noteEditorTitle.SetTextWithoutNotify(title);
                    __instance.noteTitle.text = title;
                }
                if (content != null)
                {
                    __instance.noteEditorContent.SetTextWithoutNotify(content);
                    __instance.noteContent.text = content;
                }
            }
            catch (System.Exception e)
            {
                Plugin.Log.LogWarning($"Note viewer not translated: {e.Message}");
            }
        }

        private static string Translate(string english)
        {
            if (string.IsNullOrEmpty(english)) return null;
            string pt = Plugin.Translator.Translate(english);
            return pt == null ? null : GenderMarkers.Resolve(pt);
        }
    }
}
