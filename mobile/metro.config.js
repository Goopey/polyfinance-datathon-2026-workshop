// Metro : autorise l'import des fichiers de référence partagés avec le backend
// (data/reference/personas.json), pour garder une seule source de vérité.
const path = require("path");
const { getDefaultConfig } = require("expo/metro-config");

const config = getDefaultConfig(__dirname);
config.watchFolders = [path.resolve(__dirname, "../data/reference")];

module.exports = config;
