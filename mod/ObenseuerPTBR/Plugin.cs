using System;
using System.IO;
using BepInEx;
using BepInEx.Configuration;
using BepInEx.Logging;
using HarmonyLib;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace ObenseuerPTBR
{
    [BepInPlugin(Guid, Name, Version)]
    [BepInProcess("Obenseuer.exe")]
    public sealed class Plugin : BaseUnityPlugin
    {
        public const string Guid = "redsocket.obenseuer.ptbr";
        public const string Name = "Obenseuer PT-BR";
        public const string Version = "0.4.2";
        public const string TestedGameVersion = "0.5.19";

        internal static ManualLogSource Log;
        internal static Catalog Catalog;
        internal static Translator Translator;
        internal static ConfigEntry<bool> Enabled;
        internal static ConfigEntry<string> Language;
        internal static ConfigEntry<bool> UseFuzzy;
        internal static ConfigEntry<bool> CollectUntranslated;
        internal static string UntranslatedPath;

        private void Awake()
        {
            Log = Logger;
            Enabled = Config.Bind("General", "Enabled", true,
                "Show the translation. Item names switch only after a game restart.");
            Language = Config.Bind("General", "Language", "pt-BR",
                "Folder under translations/ to load the .po files from.");
            UseFuzzy = Config.Bind("Translators", "ShowUnreviewedDrafts", true,
                "Also show translations marked fuzzy: drafts not reviewed yet, or lines whose English changed in a game update.");
            CollectUntranslated = Config.Bind("Translators", "CollectUntranslated", false,
                "Append every on-screen English label that has no translation to untranslated.po in the plugin folder.");

            if (Application.version != TestedGameVersion)
                Log.LogWarning($"Built for {TestedGameVersion}, running on {Application.version}. New or changed text will show in English.");

            string dir = Path.GetDirectoryName(Info.Location);
            UntranslatedPath = Path.Combine(dir, "untranslated.po");
            Catalog = new Catalog();
            Catalog.LoadFolder(Path.Combine(Path.Combine(dir, "translations"), Language.Value), UseFuzzy.Value);
            Translator = new Translator(Catalog, Log.LogWarning);
            Log.LogInfo($"Loaded {Catalog.Count} translations ({Translator.TemplateCount} templates, {Catalog.Fuzzy} fuzzy) for {Language.Value}");

            try { new Harmony(Guid).PatchAll(typeof(Plugin).Assembly); }
            catch (Exception e) { Log.LogError($"Patching failed: {e}"); }

            SceneManager.sceneLoaded += (scene, mode) =>
            {
                UiText.AttachAll();
                FontFallback.Check();
            };
            Enabled.SettingChanged += (s, e) => UiText.AttachAll();
        }

        private void Update() => TextFit.ApplyPending();

        private void Start()
        {
            UiText.AttachAll();
            FontFallback.Check();
            ItemText.ApplyItems();
            ItemText.ApplyRecipes();
        }
    }
}
