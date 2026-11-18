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
    [BepInDependency(ModStrings.BetterTenementGuid, BepInDependency.DependencyFlags.SoftDependency)]
    [BepInDependency(ModStrings.FairMarketGuid, BepInDependency.DependencyFlags.SoftDependency)]
    public sealed class Plugin : BaseUnityPlugin
    {
        public const string Guid = "redsocket.obenseuer.ptbr";
        public const string Name = "Obenseuer PT-BR";
        public const string Version = "0.5.1";
        public const string TestedGameVersion = "0.5.19";

        internal static ManualLogSource Log;
        internal static Catalog Catalog;
        internal static Translator Translator;
        internal static ConfigEntry<bool> Enabled;
        internal static ConfigEntry<string> Language;
        internal static ConfigEntry<bool> UseFuzzy;
        internal static ConfigEntry<bool> CollectUntranslated;
        internal static ConfigEntry<bool> TranslateTextures;
        internal static ConfigEntry<bool> FixFontAccents;
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
            TranslateTextures = Config.Bind("General", "TranslateTextures", true,
                "Replace signs, posters and other textures with text by their Portuguese versions. Takes effect on the next scene load.");
            FixFontAccents = Config.Bind("General", "FixTypewriterAccents", true,
                "Redraw the accented letters of the game's typewriter font, whose tildes and capital accents are broken. Needs a game restart.");
            CollectUntranslated = Config.Bind("Translators", "CollectUntranslated", false,
                "Append every on-screen English label that has no translation to untranslated.po in the plugin folder.");

            if (Application.version != TestedGameVersion)
                Log.LogWarning($"Built for {TestedGameVersion}, running on {Application.version}. New or changed text will show in English.");

            string dir = Path.GetDirectoryName(Info.Location);
            UntranslatedPath = Path.Combine(dir, "untranslated.po");
            Catalog = new Catalog();
            Catalog.LoadFolder(Path.Combine(Path.Combine(dir, "translations"), Language.Value), UseFuzzy.Value);
            Translator = new Translator(Catalog, Log.LogWarning);
            TextureSwap.LoadFolder(Path.Combine(Path.Combine(dir, "textures"), Language.Value));
            Log.LogInfo($"Loaded {Catalog.Count} translations ({Translator.TemplateCount} templates, {Catalog.Fuzzy} fuzzy) for {Language.Value}");

            var harmony = new Harmony(Guid);
            try { harmony.PatchAll(typeof(Plugin).Assembly); }
            catch (Exception e) { Log.LogError($"Patching failed: {e}"); }
            try { ModStrings.Apply(harmony); }
            catch (Exception e) { Log.LogWarning($"Other mods' text not translated: {e.Message}"); }

            SceneManager.sceneLoaded += (scene, mode) =>
            {
                UiText.AttachAll();
                FontFallback.Check();
                AccentGlyphs.FixAll();
                TextureSwap.Apply();
                StartCoroutine(TextureSwap.ApplyLater());
                LetterSigns.Apply();
                ButtonGap.Apply(scene);
            };
            Enabled.SettingChanged += (s, e) => UiText.AttachAll();
        }

        private void Update() => TextFit.ApplyPending();

        private void Start()
        {
            UiText.AttachAll();
            FontFallback.Check();
            AccentGlyphs.FixAll();
            ItemText.ApplyItems();
            ItemText.ApplyRecipes();
        }
    }
}
