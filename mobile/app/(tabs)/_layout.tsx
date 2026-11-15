/**
 * Onglets : Pistes à explorer, Tester une idée, Profil.
 */
import { Tabs } from "expo-router";
import { Text, type ColorValue } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { colors } from "../../src/theme/tokens";

const icon = (glyph: string) =>
  function TabIcon({ color }: { color: ColorValue }) {
    return <Text style={{ color, fontSize: 20 }}>{glyph}</Text>;
  };

export default function TabsLayout() {
  const insets = useSafeAreaInsets();
  return (
    <Tabs
      screenOptions={{
        tabBarStyle: { height: 74 + insets.bottom, paddingTop: 6, paddingBottom: 8 + insets.bottom },
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.textMuted,
        tabBarLabelStyle: { fontSize: 13, fontWeight: "600" },
        headerStyle: { backgroundColor: colors.surface },
        headerTitleStyle: { fontWeight: "700" },
        sceneStyle: { backgroundColor: colors.bg },
      }}
    >
      <Tabs.Screen name="index" options={{ title: "Pistes à explorer", tabBarLabel: "Pistes", tabBarIcon: icon("☰") }} />
      <Tabs.Screen name="tester" options={{ title: "Tester une idée", tabBarLabel: "Tester une idée", tabBarIcon: icon("?") }} />
      <Tabs.Screen name="profil" options={{ title: "Profil", tabBarLabel: "Profil", tabBarIcon: icon("◉") }} />
    </Tabs>
  );
}
