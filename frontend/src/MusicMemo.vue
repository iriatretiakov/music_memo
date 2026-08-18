<template>
  <div class="music-memo-container">
    <div class="glass-card">
      <!-- Header -->
      <header class="header">
        <h1>Music Memo</h1>
        <div class="status-dot" :class="{ active: isPlaying }"></div>
      </header>

      <!-- Current Track Section -->
      <section class="track-section">
        <div v-if="currentTrack" class="track-info animate-in">
          <p class="label">Currently Playing</p>
          <h2 class="track-name">{{ currentTrack.track_name }}</h2>
          <p class="artist-name">{{ currentTrack.artist_name }}</p>
        </div>
        <div v-else-if="authRequired" class="loading-state">
          <p>Connect Spotify to start.</p>
          <p v-if="authMessage" class="auth-message">{{ authMessage }}</p>
          <button @click="loginWithSpotify" class="spotify-btn">Connect Spotify</button>
        </div>
        <div v-else class="loading-state">
          <p>{{ trackMessage }}</p>
          <button @click="fetchCurrentTrack" class="btn-text" :disabled="isLoadingTrack">
            {{ isLoadingTrack ? 'Checking...' : 'Refresh' }}
          </button>
        </div>
      </section>

      <!-- Mood Selection -->
      <section class="mood-section">
        <p class="label text-center">How does this sound?</p>
        <div class="mood-grid">
          <button 
            v-for="mood in moods" 
            :key="mood.emoji"
            @click="selectedMood = mood.emoji"
            :class="['mood-btn', { active: selectedMood === mood.emoji }]"
          >
            <span class="emoji">{{ mood.emoji }}</span>
            <span class="mood-label">{{ mood.label }}</span>
          </button>
        </div>
      </section>

      <!-- Note Input -->
      <section class="input-section">
        <textarea 
          v-model="note" 
          placeholder="Add a quick note..."
          rows="3"
        ></textarea>
      </section>

      <!-- Save Button -->
      <footer class="footer">
        <button 
          @click="saveEntry" 
          :disabled="!canSave || isSaving"
          class="save-btn"
        >
          <span v-if="!isSaving">Save Memo</span>
          <span v-else class="spinner"></span>
        </button>
      </footer>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue';

// State
const currentTrack = ref(null);
const selectedMood = ref(null);
const note = ref('');
const isSaving = ref(false);
const isLoadingTrack = ref(false);
const authRequired = ref(false);
const authMessage = ref('');
const trackMessage = ref("Nothin' spinning right now...");
const userId = ref(null);
let pollTimer = null;

const isPlaying = computed(() => !!currentTrack.value?.track_id);
const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '');
const configuredUserId = Number(import.meta.env.VITE_USER_ID || 0);

const moods = [
  { emoji: '🔥', label: 'Hype' },
  { emoji: '✨', label: 'Chill' },
  { emoji: '😢', label: 'Sad' },
  { emoji: '🤘', label: 'Rock' },
  { emoji: '🌈', label: 'Happy' },
  { emoji: '🌪️', label: 'Vibe' },
];

const canSave = computed(() => currentTrack.value && selectedMood.value && userId.value);

// API Calls
const apiUrl = (path) => `${apiBaseUrl}${path.startsWith('/') ? path : `/${path}`}`;

const parseUserId = (value) => {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
};

const getCookie = (name) => {
  const cookie = document.cookie
    .split('; ')
    .find((item) => item.startsWith(`${name}=`));

  return cookie ? decodeURIComponent(cookie.split('=').slice(1).join('=')) : null;
};

const rememberUserId = (value) => {
  userId.value = value;
  localStorage.setItem('music_memo_user_id', String(value));
};

const loadStoredUserId = () => (
  parseUserId(localStorage.getItem('music_memo_user_id')) ||
  parseUserId(getCookie('music_memo_user_id')) ||
  parseUserId(configuredUserId)
);

const readAuthCallbackParams = () => {
  const params = new URLSearchParams(window.location.search);
  const callbackUserId = parseUserId(params.get('user_id'));
  const authError = params.get('auth_error');
  let shouldCleanUrl = false;

  if (callbackUserId) {
    rememberUserId(callbackUserId);
    authRequired.value = false;
    authMessage.value = '';
    params.delete('user_id');
    params.delete('auth');
    shouldCleanUrl = true;
  }

  if (authError) {
    authRequired.value = true;
    authMessage.value = 'Spotify authorization failed.';
    params.delete('auth_error');
    shouldCleanUrl = true;
  }

  if (shouldCleanUrl) {
    const query = params.toString();
    const nextUrl = `${window.location.pathname}${query ? `?${query}` : ''}${window.location.hash}`;
    window.history.replaceState({}, '', nextUrl);
  }
};

const loginWithSpotify = () => {
  window.location.href = apiUrl('/auth/login');
};

const fetchCurrentTrack = async () => {
  if (!userId.value) {
    authRequired.value = true;
    authMessage.value = '';
    currentTrack.value = null;
    return;
  }

  isLoadingTrack.value = true;

  try {
    const response = await fetch(apiUrl(`/auth/me/current-track?user_id=${userId.value}`));
    const data = await response.json();

    if (response.status === 404) {
      localStorage.removeItem('music_memo_user_id');
      userId.value = null;
      authRequired.value = true;
      authMessage.value = 'Spotify is not connected yet.';
      currentTrack.value = null;
      return;
    }

    if (!response.ok) {
      throw new Error(data.detail || 'Failed to fetch track');
    }

    authRequired.value = false;
    authMessage.value = '';

    if (data.track_id) {
      currentTrack.value = data;
    } else {
      currentTrack.value = null;
      trackMessage.value = data.message || "Nothin' spinning right now...";
    }
  } catch (error) {
    currentTrack.value = null;
    trackMessage.value = 'Could not reach Music Memo API.';
    console.error('Failed to fetch track', error);
  } finally {
    isLoadingTrack.value = false;
  }
};

const saveEntry = async () => {
  if (!canSave.value) {
    if (!userId.value) {
      authRequired.value = true;
    }
    return;
  }

  isSaving.value = true;
  
  try {
    const response = await fetch(apiUrl('/entries/'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: userId.value,
        track_id: currentTrack.value.track_id,
        track_name: currentTrack.value.track_name,
        artist_name: currentTrack.value.artist_name,
        mood: selectedMood.value,
        note: note.value
      })
    });

    if (response.ok) {
      // Success feedback
      note.value = '';
      selectedMood.value = null;
      alert('Memo saved! Keep listening. 🎵');
    }
  } catch (error) {
    console.error('Failed to save entry', error);
  } finally {
    isSaving.value = false;
  }
};

onMounted(() => {
  readAuthCallbackParams();
  userId.value = userId.value || loadStoredUserId();
  fetchCurrentTrack();
  pollTimer = setInterval(() => {
    if (!authRequired.value) {
      fetchCurrentTrack();
    }
  }, 30000);
});

onUnmounted(() => {
  if (pollTimer) {
    clearInterval(pollTimer);
  }
});
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;500;700&display=swap');

.music-memo-container {
  min-height: 100vh;
  background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
  font-family: 'Outfit', sans-serif;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  color: white;
}

.glass-card {
  width: 100%;
  max-width: 400px;
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 32px;
  padding: 32px;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 32px;
}

h1 {
  font-size: 20px;
  font-weight: 700;
  letter-spacing: -0.5px;
  margin: 0;
  opacity: 0.8;
}

.status-dot {
  width: 8px;
  height: 8px;
  background: #ff4b2b;
  border-radius: 50%;
  box-shadow: 0 0 10px #ff4b2b;
}

.status-dot.active {
  background: #00ff88;
  box-shadow: 0 0 10px #00ff88;
  animation: pulse 2s infinite;
}

.track-section {
  margin-bottom: 40px;
  min-height: 100px;
}

.label {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 1px;
  opacity: 0.5;
  margin-bottom: 8px;
}

.track-name {
  font-size: 28px;
  margin: 0;
  line-height: 1.2;
}

.artist-name {
  font-size: 18px;
  opacity: 0.7;
  margin: 8px 0 0 0;
}

.mood-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-top: 16px;
  margin-bottom: 32px;
}

.mood-btn {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 20px;
  padding: 16px 8px;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  flex-direction: column;
  align-items: center;
}

.mood-btn:hover {
  background: rgba(255, 255, 255, 0.1);
}

.mood-btn.active {
  background: rgba(255, 255, 255, 0.15);
  border-color: rgba(255, 255, 255, 0.4);
  transform: scale(1.05);
}

.emoji {
  font-size: 24px;
  margin-bottom: 4px;
}

.mood-label {
  font-size: 10px;
  text-transform: uppercase;
  opacity: 0.6;
}

textarea {
  width: 100%;
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  padding: 16px;
  color: white;
  font-family: inherit;
  resize: none;
  font-size: 14px;
  box-sizing: border-box;
}

textarea:focus {
  outline: none;
  border-color: rgba(255, 255, 255, 0.3);
}

.footer {
  margin-top: 32px;
}

.save-btn {
  width: 100%;
  background: white;
  color: black;
  border: none;
  border-radius: 100px;
  padding: 18px;
  font-weight: 700;
  font-size: 16px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.save-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.save-btn:active:not(:disabled) {
  transform: scale(0.97);
}

@keyframes pulse {
  0% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.5); opacity: 0.5; }
  100% { transform: scale(1); opacity: 1; }
}

.animate-in {
  animation: slideUp 0.6s ease-out;
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.btn-text {
  background: none;
  border: none;
  color: #00ff88;
  cursor: pointer;
  text-decoration: underline;
  padding: 0;
  font-size: 14px;
}

.btn-text:disabled {
  opacity: 0.6;
  cursor: wait;
}

.auth-message {
  font-size: 13px;
  opacity: 0.65;
  margin: 8px 0 16px;
}

.spotify-btn {
  background: #1ed760;
  border: none;
  border-radius: 100px;
  color: #07130a;
  cursor: pointer;
  font-family: inherit;
  font-size: 14px;
  font-weight: 700;
  padding: 12px 18px;
  transition: transform 0.2s ease, background 0.2s ease;
}

.spotify-btn:hover {
  background: #32e06f;
}

.spotify-btn:active {
  transform: scale(0.97);
}
</style>
