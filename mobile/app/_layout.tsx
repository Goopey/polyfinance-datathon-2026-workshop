/**
 * Mise en page racine : fournisseurs (requêtes, gestes, zones sûres), thème sombre, pile de navigation.
 * Le coin supérieur droit de chaque en-tête porte le sélecteur de langue FR / EN.
 * Conception : docs/07_UX_UI.md
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { useEffect, useState } from "react";
import { Platform, View } from "react-native";
import { GestureHandlerRootView } from "react-native-gesture-handler";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { HeaderActions } from "../src/components/HeaderActions";
import { useT } from "../src/i18n";
import { useSettings } from "../src/store/settings";
import { colors } from "../src/theme/tokens";
import { fontFamily } from "../src/theme/typography";

/** Web : police Inter, fond sombre dès le premier rendu, attribut lang du document. */
function useWebSetup(lang: string) {
  useEffect(() => {
    if (Platform.OS !== "web" || typeof document === "undefined") return;
    if (!document.getElementById("font-inter")) {
      const pre = document.createElement("link");
      pre.rel = "preconnect";
      pre.href = "https://fonts.gstatic.com";
      pre.crossOrigin = "anonymous";
      const link = document.createElement("link");
      link.id = "font-inter";
      link.rel = "stylesheet";
      link.href = "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap";
      document.head.append(pre, link);
    }
    document.body.style.backgroundColor = colors.bg;
    document.documentElement.style.colorScheme = "dark";
  }, []);
  useEffect(() => {
    if (Platform.OS === "web" && typeof document !== "undefined") document.documentElement.lang = lang;
  }, [lang]);
}

export default function RootLayout() {
  const [client] = useState(() => new QueryClient({ defaultOptions: { queries: { staleTime: 60_000, retry: 1 } } }));
  const lang = useSettings((s) => s.lang);
  const t = useT();
  useWebSetup(lang);
  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <QueryClientProvider client={client}>
          <StatusBar style="light" />
          <View style={{ flex: 1, backgroundColor: colors.bg }}>
            <Stack
              screenOptions={{
                headerStyle: { backgroundColor: colors.bg },
                headerShadowVisible: false,
                headerTintColor: colors.mint,
                headerTitleStyle: { fontWeight: "700", fontFamily, color: colors.text },
                contentStyle: { backgroundColor: colors.bg },
                headerBackTitle: t.common.back,
                headerRight: () => <HeaderActions />,
              }}
            >
              <Stack.Screen name="index" options={{ headerShown: false }} />
              <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
              <Stack.Screen name="onboarding/index" options={{ headerShown: false }} />
              <Stack.Screen name="onboarding/questionnaire" options={{ title: t.nav.questionnaire }} />
              <Stack.Screen name="onboarding/resume" options={{ title: t.nav.resume }} />
              <Stack.Screen name="piste/[ticker]" options={{ title: t.nav.piste }} />
              <Stack.Screen name="preuve/[id]" options={{ title: t.nav.preuve, presentation: "modal" }} />
              <Stack.Screen name="run/[id]" options={{ title: t.nav.run }} />
              <Stack.Screen name="comparer" options={{ title: t.nav.comparer }} />
              <Stack.Screen name="donnees" options={{ title: t.nav.donnees }} />
            </Stack>
          </View>
        </QueryClientProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}
