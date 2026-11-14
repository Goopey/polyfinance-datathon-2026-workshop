/** Stockage persistant pour zustand (AsyncStorage ; localStorage sur le web). */
import AsyncStorage from "@react-native-async-storage/async-storage";
import { createJSONStorage } from "zustand/middleware";

export const persistStorage = createJSONStorage(() => AsyncStorage);
