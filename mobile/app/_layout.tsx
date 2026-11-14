/**
 * Mise en page racine : fournisseurs (requêtes, gestes, zones sûres), bandeau de simulation permanent, pile de navigation.
 * Conception : docs/07_UX_UI.md
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { useState } from "react";
import { View } from "react-native";
import { GestureHandlerRootView } from "react-native-gesture-handler";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { SimulationBanner } from "../src/components/SimulationBanner";
import { colors } from "../src/theme/tokens";

export default function RootLayout() {
  const [client] = useState(() => new QueryClient({ defaultOptions: { queries: { staleTime: 60_000, retry: 1 } } }));
  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <QueryClientProvider client={client}>
          <StatusBar style="light" />
          <View style={{ flex: 1, backgroundColor: colors.bg }}>
            <SimulationBanner />
            <Stack
              screenOptions={{
                headerStyle: { backgroundColor: colors.surface },
                headerTintColor: colors.text,
                headerTitleStyle: { fontWeight: "700" },
                contentStyle: { backgroundColor: colors.bg },
                headerBackTitle: "Retour",
              }}
            >
              <Stack.Screen name="index" options={{ headerShown: false }} />
              <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
              <Stack.Screen name="onboarding/index" options={{ headerShown: false }} />
              <Stack.Screen name="onboarding/questionnaire" options={{ title: "Créer un profil fictif" }} />
              <Stack.Screen name="onboarding/resume" options={{ title: "Votre profil" }} />
              <Stack.Screen name="piste/[ticker]" options={{ title: "Fiche de la piste" }} />
              <Stack.Screen name="preuve/[id]" options={{ title: "Pourquoi ? — la preuve", presentation: "modal" }} />
              <Stack.Screen name="run/[id]" options={{ title: "Parcours de l'analyse" }} />
              <Stack.Screen name="comparer" options={{ title: "Comparer deux profils" }} />
              <Stack.Screen name="donnees" options={{ title: "Données et sources" }} />
            </Stack>
          </View>
        </QueryClientProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}
