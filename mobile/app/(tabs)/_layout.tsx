/**
 * Onglets : Pistes à explorer, Tester une idée, Profil. Icônes vectorielles ; sélecteur de langue en haut à droite.
 */
import { Tabs } from "expo-router";
import type { ColorValue } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { HeaderActions } from "../../src/components/HeaderActions";
import { Icon, type IconName } from "../../src/components/Icon";
import { useT } from "../../src/i18n";
import { colors } from "../../src/theme/tokens";
import { fontFamily } from "../../src/theme/typography";

const icon = (name: IconName) =>
  function TabIcon({ color }: { color: ColorValue }) {
    return <Icon name={name} size={22} color={String(color)} />;
  };

export default function TabsLayout() {
  const insets = useSafeAreaInsets();
  const t = useT();
  return (
    <Tabs
      screenOptions={{
        tabBarStyle: {
          height: 70 + insets.bottom, paddingTop: 8, paddingBottom: 8 + insets.bottom,
          backgroundColor: colors.surface, borderTopColor: colors.border, borderTopWidth: 1,
        },
        tabBarActiveTintColor: colors.mint,
        tabBarInactiveTintColor: colors.textSubtle,
        tabBarLabelStyle: { fontSize: 12.5, fontWeight: "600", fontFamily },
        headerStyle: { backgroundColor: colors.bg },
        headerShadowVisible: false,
        headerTintColor: colors.mint,
        headerTitleStyle: { fontWeight: "800", fontFamily, color: colors.text },
        headerRight: () => <HeaderActions />,
        sceneStyle: { backgroundColor: colors.bg },
      }}
    >
      <Tabs.Screen name="index" options={{ title: t.nav.pistes, tabBarLabel: t.nav.pistesTab, tabBarIcon: icon("compass") }} />
      <Tabs.Screen name="tester" options={{ title: t.nav.tester, tabBarLabel: t.nav.testerTab, tabBarIcon: icon("flask") }} />
      <Tabs.Screen name="profil" options={{ title: t.nav.profil, tabBarLabel: t.nav.profil, tabBarIcon: icon("user") }} />
    </Tabs>
  );
}
