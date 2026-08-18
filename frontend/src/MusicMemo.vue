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

      <section v-if="currentTrack && pastTrackEntries.length" class="track-memory-section animate-in">
        <div class="section-header">
          <p class="label">Past notes on this track</p>
          <span class="entry-count">{{ pastTrackEntries.length }}</span>
        </div>
        <div class="memo-list compact">
          <article v-for="entry in pastTrackEntries" :key="entry.id" class="memo-row">
            <template v-if="pendingDeleteId === entry.id">
              <div class="delete-confirm">
                <p>Delete this memo?</p>
                <div class="delete-actions">
                  <button @click="cancelDelete" class="delete-secondary" :disabled="deletingEntryId === entry.id">
                    Cancel
                  </button>
                  <button @click="deleteEntry(entry)" class="delete-danger" :disabled="deletingEntryId === entry.id">
                    {{ deletingEntryId === entry.id ? 'Deleting...' : 'Delete' }}
                  </button>
                </div>
              </div>
            </template>
            <template v-else>
              <span class="memo-mood">{{ entry.mood }}</span>
              <div class="memo-body">
                <div class="memo-title-row">
                  <p class="memo-note">{{ entry.note || 'No note' }}</p>
                  <span class="memo-time">{{ formatEntryTime(entry.created_at) }}</span>
                </div>
              </div>
              <button @click="requestDelete(entry.id)" class="memo-delete" aria-label="Delete memo">
                ×
              </button>
            </template>
          </article>
        </div>
      </section>

      <!-- Mood Selection -->
      <section class="mood-section">
        <p class="label text-center">How does this sound?</p>
        <div class="mood-grid">
          <button 
            v-for="mood in moods" 
            :key="mood.emoji"
            @click="selectPresetMood(mood.emoji)"
            :class="['mood-btn', { active: selectedMood === mood.emoji }]"
          >
            <span class="emoji">{{ mood.emoji }}</span>
            <span class="mood-label">{{ mood.label }}</span>
          </button>
        </div>
        <div :class="['custom-mood', { active: isCustomMoodSelected }]">
          <span class="custom-mood-preview">{{ customMood || '🙂' }}</span>
          <input
            v-model="customMood"
            @input="selectCustomMood"
            class="custom-mood-input"
            type="text"
            maxlength="32"
            autocomplete="off"
            autocapitalize="off"
            spellcheck="false"
            aria-label="Custom emoji"
            placeholder="🙂"
          />
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
          :class="['save-btn', { saved: saveStatus === 'saved' }]"
        >
          <span v-if="!isSaving">{{ saveButtonLabel }}</span>
          <span v-else class="spinner"></span>
        </button>
        <p v-if="saveMessage" :class="['save-message', { error: saveStatus === 'error' }]">
          {{ saveMessage }}
        </p>
      </footer>

      <section v-if="recentEntries.length" class="feed-section">
        <div class="section-header">
          <p class="label">Recent memos</p>
          <span class="entry-count">{{ recentEntries.length }}</span>
        </div>
        <div class="memo-list">
          <article v-for="entry in recentEntries" :key="entry.id" class="memo-row">
            <template v-if="pendingDeleteId === entry.id">
              <div class="delete-confirm">
                <p>Delete this memo?</p>
                <div class="delete-actions">
                  <button @click="cancelDelete" class="delete-secondary" :disabled="deletingEntryId === entry.id">
                    Cancel
                  </button>
                  <button @click="deleteEntry(entry)" class="delete-danger" :disabled="deletingEntryId === entry.id">
                    {{ deletingEntryId === entry.id ? 'Deleting...' : 'Delete' }}
                  </button>
                </div>
              </div>
            </template>
            <template v-else>
              <span class="memo-mood">{{ entry.mood }}</span>
              <div class="memo-body">
                <div class="memo-title-row">
                  <p class="memo-track">{{ entry.track_name }}</p>
                  <span class="memo-time">{{ formatEntryTime(entry.created_at) }}</span>
                </div>
                <p class="memo-artist">{{ entry.artist_name }}</p>
                <p v-if="entry.note" class="memo-note">{{ entry.note }}</p>
              </div>
              <button @click="requestDelete(entry.id)" class="memo-delete" aria-label="Delete memo">
                ×
              </button>
            </template>
          </article>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue';

// State
const currentTrack = ref(null);
const selectedMood = ref(null);
const customMood = ref('');
const note = ref('');
const isSaving = ref(false);
const isLoadingTrack = ref(false);
const authRequired = ref(false);
const authMessage = ref('');
const trackMessage = ref("Nothin' spinning right now...");
const userId = ref(null);
const pastTrackEntries = ref([]);
const recentEntries = ref([]);
const saveStatus = ref('idle');
const saveMessage = ref('');
const pendingDeleteId = ref(null);
const deletingEntryId = ref(null);
let pollTimer = null;
let saveMessageTimer = null;

const ACTIVE_TRACK_POLL_MS = 5000;
const HIDDEN_TRACK_POLL_MS = 30000;
const RECENT_ENTRIES_LIMIT = 20;
const TRACK_ENTRIES_LIMIT = 5;

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
const isCustomMoodSelected = computed(() => customMood.value && selectedMood.value === customMood.value);
const saveButtonLabel = computed(() => (saveStatus.value === 'saved' ? 'Saved' : 'Save Memo'));

const emojiPattern = /\p{Extended_Pictographic}|\p{Regional_Indicator}|\p{Emoji_Presentation}|\p{Emoji}\uFE0F/u;

const getGraphemes = (value) => {
  if (typeof Intl !== 'undefined' && Intl.Segmenter) {
    return Array.from(
      new Intl.Segmenter(undefined, { granularity: 'grapheme' }).segment(value),
      (item) => item.segment
    );
  }

  return Array.from(value);
};

const firstEmojiFrom = (value) => (
  getGraphemes(value.trim()).find((segment) => emojiPattern.test(segment)) || ''
);

const selectPresetMood = (emoji) => {
  selectedMood.value = emoji;
  customMood.value = '';
};

const selectCustomMood = () => {
  const emoji = firstEmojiFrom(customMood.value);
  customMood.value = emoji;
  selectedMood.value = emoji || null;
};

const formatEntryTime = (value) => {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return '';
  }

  const now = new Date();
  const isToday = date.toDateString() === now.toDateString();

  return new Intl.DateTimeFormat(undefined, {
    month: isToday ? undefined : 'short',
    day: isToday ? undefined : 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
};

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
  fetch(apiUrl('/auth/login-url'))
    .then((response) => {
      if (!response.ok) {
        throw new Error('Spotify auth is not configured');
      }
      return response.json();
    })
    .then((data) => {
      window.location.href = data.url;
    })
    .catch((error) => {
      authMessage.value = 'Could not start Spotify authorization.';
      console.error('Failed to start Spotify auth', error);
    });
};

const fetchCurrentTrack = async () => {
  if (!userId.value) {
    authRequired.value = true;
    authMessage.value = '';
    currentTrack.value = null;
    return;
  }

  if (isLoadingTrack.value) {
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
      const previousTrackId = currentTrack.value?.track_id;
      currentTrack.value = data;

      if (data.track_id !== previousTrackId) {
        fetchTrackEntries(data.track_id);
      }
    } else {
      currentTrack.value = null;
      pastTrackEntries.value = [];
      trackMessage.value = data.message || "Nothin' spinning right now...";
    }
  } catch (error) {
    currentTrack.value = null;
    pastTrackEntries.value = [];
    trackMessage.value = 'Could not reach Music Memo API.';
    console.error('Failed to fetch track', error);
  } finally {
    isLoadingTrack.value = false;
  }
};

const trackPollDelay = () => (
  document.visibilityState === 'visible' ? ACTIVE_TRACK_POLL_MS : HIDDEN_TRACK_POLL_MS
);

const clearTrackPoll = () => {
  if (pollTimer) {
    clearTimeout(pollTimer);
    pollTimer = null;
  }
};

const scheduleTrackPoll = () => {
  clearTrackPoll();
  pollTimer = setTimeout(runTrackPoll, trackPollDelay());
};

const runTrackPoll = async () => {
  if (!authRequired.value) {
    await fetchCurrentTrack();
  }

  scheduleTrackPoll();
};

const handleVisibilityChange = () => {
  scheduleTrackPoll();

  if (document.visibilityState === 'visible' && !authRequired.value) {
    fetchCurrentTrack();
  }
};

const fetchRecentEntries = async () => {
  if (!userId.value) {
    recentEntries.value = [];
    return;
  }

  try {
    const response = await fetch(apiUrl(`/entries/?user_id=${userId.value}&limit=${RECENT_ENTRIES_LIMIT}`));
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || 'Failed to fetch recent memos');
    }

    recentEntries.value = data;
  } catch (error) {
    console.error('Failed to fetch recent memos', error);
  }
};

const fetchTrackEntries = async (trackId = currentTrack.value?.track_id) => {
  if (!userId.value || !trackId) {
    pastTrackEntries.value = [];
    return;
  }

  try {
    const response = await fetch(
      apiUrl(`/entries/track/${encodeURIComponent(trackId)}?user_id=${userId.value}&limit=${TRACK_ENTRIES_LIMIT}`)
    );
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || 'Failed to fetch track memos');
    }

    pastTrackEntries.value = data;
  } catch (error) {
    console.error('Failed to fetch track memos', error);
  }
};

const prependEntry = (entries, entry, limit) => [
  entry,
  ...entries.filter((item) => item.id !== entry.id),
].slice(0, limit);

const removeEntryFromLists = (entryId) => {
  pastTrackEntries.value = pastTrackEntries.value.filter((entry) => entry.id !== entryId);
  recentEntries.value = recentEntries.value.filter((entry) => entry.id !== entryId);
};

const clearSaveMessage = () => {
  if (saveMessageTimer) {
    clearTimeout(saveMessageTimer);
    saveMessageTimer = null;
  }
};

const showSaveFeedback = (status, message) => {
  clearSaveMessage();
  saveStatus.value = status;
  saveMessage.value = message;
  saveMessageTimer = setTimeout(() => {
    saveStatus.value = 'idle';
    saveMessage.value = '';
    saveMessageTimer = null;
  }, status === 'error' ? 4200 : 2200);
};

const requestDelete = (entryId) => {
  pendingDeleteId.value = entryId;
  saveStatus.value = 'idle';
  saveMessage.value = '';
};

const cancelDelete = () => {
  if (!deletingEntryId.value) {
    pendingDeleteId.value = null;
  }
};

const deleteEntry = async (entry) => {
  if (!userId.value || deletingEntryId.value) {
    return;
  }

  deletingEntryId.value = entry.id;

  try {
    const response = await fetch(apiUrl(`/entries/${entry.id}?user_id=${userId.value}`), {
      method: 'DELETE',
    });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || 'Failed to delete memo');
    }

    removeEntryFromLists(entry.id);
    pendingDeleteId.value = null;
    showSaveFeedback('saved', 'Memo deleted.');
  } catch (error) {
    showSaveFeedback('error', 'Could not delete memo.');
    console.error('Failed to delete entry', error);
  } finally {
    deletingEntryId.value = null;
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
    const savedEntry = await response.json();

    if (!response.ok) {
      throw new Error(savedEntry.detail || 'Failed to save memo');
    }

    note.value = '';
    selectedMood.value = null;
    customMood.value = '';
    pastTrackEntries.value = prependEntry(pastTrackEntries.value, savedEntry, TRACK_ENTRIES_LIMIT);
    recentEntries.value = prependEntry(recentEntries.value, savedEntry, RECENT_ENTRIES_LIMIT);
    showSaveFeedback('saved', 'Saved to your memo feed.');
  } catch (error) {
    showSaveFeedback('error', 'Could not save memo.');
    console.error('Failed to save entry', error);
  } finally {
    isSaving.value = false;
  }
};

onMounted(() => {
  readAuthCallbackParams();
  userId.value = userId.value || loadStoredUserId();
  fetchCurrentTrack();
  fetchRecentEntries();
  scheduleTrackPoll();
  document.addEventListener('visibilitychange', handleVisibilityChange);
});

onUnmounted(() => {
  clearTrackPoll();
  clearSaveMessage();
  document.removeEventListener('visibilitychange', handleVisibilityChange);
});
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;500;700&display=swap');

:global(html),
:global(body),
:global(#app) {
  margin: 0;
  min-height: 100%;
  background: #0f0c29;
}

:global(body) {
  overflow-x: hidden;
}

.music-memo-container {
  min-height: 100dvh;
  width: 100%;
  box-sizing: border-box;
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
  margin-bottom: 28px;
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

.track-memory-section,
.feed-section {
  margin-bottom: 32px;
}

.feed-section {
  margin-top: 32px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.section-header .label {
  margin: 0;
}

.entry-count {
  min-width: 24px;
  height: 24px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.72);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
}

.memo-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.memo-list.compact {
  gap: 8px;
}

.memo-row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 0;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  min-height: 36px;
}

.memo-list .memo-row:first-child {
  border-top: none;
  padding-top: 0;
}

.memo-mood {
  width: 36px;
  height: 36px;
  flex: 0 0 auto;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.06);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
}

.memo-body {
  flex: 1;
  min-width: 0;
}

.memo-title-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
}

.memo-track,
.memo-note,
.memo-artist,
.memo-time {
  margin: 0;
}

.memo-track {
  color: rgba(255, 255, 255, 0.9);
  font-size: 14px;
  font-weight: 700;
  line-height: 1.25;
  overflow-wrap: anywhere;
}

.memo-artist {
  color: rgba(255, 255, 255, 0.55);
  font-size: 12px;
  line-height: 1.35;
  margin-top: 3px;
  overflow-wrap: anywhere;
}

.memo-note {
  color: rgba(255, 255, 255, 0.76);
  font-size: 13px;
  line-height: 1.4;
  margin-top: 6px;
  overflow-wrap: anywhere;
}

.track-memory-section .memo-note {
  margin-top: 0;
}

.memo-time {
  color: rgba(255, 255, 255, 0.42);
  flex: 0 0 auto;
  font-size: 11px;
  font-weight: 500;
}

.memo-delete {
  width: 28px;
  height: 28px;
  flex: 0 0 auto;
  border: none;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.05);
  color: rgba(255, 255, 255, 0.48);
  cursor: pointer;
  font-family: inherit;
  font-size: 20px;
  line-height: 1;
  padding: 0;
  transition: background 0.2s ease, color 0.2s ease, transform 0.2s ease;
}

.memo-delete:hover {
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.82);
}

.memo-delete:active {
  transform: scale(0.94);
}

.delete-confirm {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.06);
  padding: 10px 12px;
}

.delete-confirm p {
  color: rgba(255, 255, 255, 0.86);
  font-size: 13px;
  font-weight: 700;
  line-height: 1.25;
  margin: 0;
}

.delete-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 0 0 auto;
}

.delete-secondary,
.delete-danger {
  border: none;
  border-radius: 999px;
  cursor: pointer;
  font-family: inherit;
  font-size: 12px;
  font-weight: 700;
  padding: 8px 11px;
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.delete-secondary {
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.72);
}

.delete-danger {
  background: #ff6f61;
  color: #1c0806;
}

.delete-secondary:disabled,
.delete-danger:disabled {
  cursor: wait;
  opacity: 0.62;
}

.delete-secondary:active:not(:disabled),
.delete-danger:active:not(:disabled) {
  transform: scale(0.96);
}

.mood-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-top: 16px;
  margin-bottom: 12px;
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

.custom-mood {
  display: flex;
  align-items: center;
  gap: 12px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 16px;
  margin-bottom: 32px;
  padding: 10px 12px;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.custom-mood:focus-within,
.custom-mood:hover {
  background: rgba(255, 255, 255, 0.1);
}

.custom-mood.active {
  background: rgba(255, 255, 255, 0.15);
  border-color: rgba(255, 255, 255, 0.4);
}

.custom-mood-preview {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: rgba(0, 0, 0, 0.16);
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  font-size: 24px;
}

.custom-mood-input {
  width: 100%;
  min-width: 0;
  background: transparent;
  border: none;
  color: white;
  font-family: inherit;
  font-size: 22px;
  line-height: 1;
  padding: 10px 0;
}

.custom-mood-input:focus {
  outline: none;
}

.custom-mood-input::placeholder {
  color: rgba(255, 255, 255, 0.4);
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

.save-btn.saved {
  background: #00ff88;
  color: #07130a;
}

.save-btn:active:not(:disabled) {
  transform: scale(0.97);
}

.save-message {
  color: rgba(255, 255, 255, 0.62);
  font-size: 12px;
  line-height: 1.4;
  margin: 10px 0 0;
  text-align: center;
}

.save-message.error {
  color: #ff9a8d;
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
