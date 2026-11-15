using System.Collections.Generic;
using System.Reflection;
using System.Reflection.Emit;
using HarmonyLib;

namespace ObenseuerPTBR
{
    /// <summary>
    /// Item titles/descriptions and recipe names. The game reads Item.Title and Recipe.Name directly in
    /// dozens of display sites, so the in-memory databases are translated once after they load.
    /// Items.json and Recipes.json on disk are never touched, and both are saved by ID, so saves do not
    /// depend on the translation.
    /// </summary>
    internal static class ItemText
    {
        // English names of translated entries, by reference (both databases are parsed once per process).
        private static readonly Dictionary<Item, string> englishTitles = new Dictionary<Item, string>();
        private static readonly Dictionary<Recipe, string> englishRecipes = new Dictionary<Recipe, string>();

        public static string EnglishTitle(Item item)
        {
            if (item == null) return null;
            return englishTitles.TryGetValue(item, out string title) ? title : item.Title;
        }

        public static string EnglishRecipeName(Recipe recipe)
        {
            if (recipe == null) return null;
            return englishRecipes.TryGetValue(recipe, out string name) ? name : recipe.Name;
        }

        public static void ApplyItems()
        {
            Catalog cat = Plugin.Catalog;
            if (cat == null || ItemDatabase.database == null) return;
            int done = 0;
            foreach (Item item in ItemDatabase.database)
            {
                if (item == null || englishTitles.ContainsKey(item)) continue;
                englishTitles[item] = item.Title;
                if (cat.TryKey($"item.{item.ID}.title", out string title)) { item.Title = title; done++; }
                if (cat.TryKey($"item.{item.ID}.desc", out string desc)) item.Description = desc;
            }
            if (done > 0) Plugin.Log.LogInfo($"Translated {done} item titles");
        }

        public static void ApplyRecipes()
        {
            Catalog cat = Plugin.Catalog;
            if (cat == null || RecipeDatabase.Recipes == null) return;
            int done = 0;
            foreach (Recipe recipe in RecipeDatabase.Recipes)
            {
                if (recipe == null || englishRecipes.ContainsKey(recipe)) continue;
                englishRecipes[recipe] = recipe.Name;
                if (cat.TryKey($"recipe.{recipe.ID}.name", out string name)) { recipe.Name = name; done++; }
            }
            if (done > 0) Plugin.Log.LogInfo($"Translated {done} recipe names");
        }
    }

    [HarmonyPatch]
    internal static class ItemDatabaseLoadPatch
    {
        private static IEnumerable<MethodBase> TargetMethods()
        {
            yield return AccessTools.Method(typeof(ItemDatabase), nameof(ItemDatabase.Awake));
            yield return AccessTools.Method(typeof(ItemDatabase), nameof(ItemDatabase.OnEnable));
            yield return AccessTools.Method(typeof(ItemDatabase), nameof(ItemDatabase.Reload));
        }

        private static void Postfix() => ItemText.ApplyItems();
    }

    [HarmonyPatch(typeof(RecipeDatabase), nameof(RecipeDatabase.LoadDatabase))]
    internal static class RecipeDatabaseLoadPatch
    {
        private static void Postfix() => ItemText.ApplyRecipes();
    }

    /// <summary>
    /// Game logic that matches items or recipes by their English names: storage and trade filters
    /// ("_item_Toilet Paper"), a recipe's main output (recipe name words vs item title) and the
    /// prefab-by-title fallback. Every read of Item.Title / Recipe.Name in these methods gets the English.
    /// </summary>
    [HarmonyPatch]
    internal static class EnglishNameLogicPatch
    {
        private static readonly FieldInfo TitleField = AccessTools.Field(typeof(Item), nameof(Item.Title));
        private static readonly FieldInfo RecipeNameField = AccessTools.Field(typeof(Recipe), nameof(Recipe.Name));
        private static readonly MethodInfo EnglishTitle = AccessTools.Method(typeof(ItemText), nameof(ItemText.EnglishTitle));
        private static readonly MethodInfo EnglishRecipeName = AccessTools.Method(typeof(ItemText), nameof(ItemText.EnglishRecipeName));

        private static IEnumerable<MethodBase> TargetMethods()
        {
            yield return AccessTools.Method(typeof(SlotController), nameof(SlotController.CheckIfInAllowedCategoy));
            yield return AccessTools.Method(typeof(Recipe), nameof(Recipe.GetMainOutput));
            yield return AccessTools.Method(typeof(Item.ItemAppearance), nameof(Item.ItemAppearance.Loadprefab));
        }

        private static IEnumerable<CodeInstruction> Transpiler(IEnumerable<CodeInstruction> code, MethodBase original)
        {
            int n = 0;
            foreach (CodeInstruction ins in code)
            {
                MethodInfo english = ins.opcode != OpCodes.Ldfld ? null
                    : Equals(ins.operand, TitleField) ? EnglishTitle
                    : Equals(ins.operand, RecipeNameField) ? EnglishRecipeName
                    : null;
                if (english != null)
                {
                    n++;
                    yield return new CodeInstruction(OpCodes.Call, english).WithLabels(ins.labels).WithBlocks(ins.blocks);
                    continue;
                }
                yield return ins;
            }
            Plugin.Log.LogDebug($"{original.DeclaringType?.Name}.{original.Name}: {n} name reads kept in English");
        }
    }
}
