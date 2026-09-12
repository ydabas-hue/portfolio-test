import raw from '../data/social.json';
import { parseSocial } from './social-schema.js';

export const social = parseSocial(raw);
export const mostViewedVideos = [...social.videos]
  .filter((v) => v.views != null)
  .sort((a, b) => (b.views ?? 0) - (a.views ?? 0))
  .slice(0, 6);
export const mostEngagedPosts = [...social.posts]
  .filter((p) => p.likes != null)
  .sort((a, b) => (b.likes ?? 0) - (a.likes ?? 0))
  .slice(0, 4);

export const featuredVideos = mostViewedVideos;
export const featuredPosts = mostEngagedPosts;

/** @param {'instagram' | 'youtube' | 'linkedin'} platform */
export const profilesBy = (platform) => social.profiles.filter((p) => p.platform === platform);

const thumbs = import.meta.glob('../assets/social/*.jpg', { eager: true, import: 'default' });
/** @param {string} fileName e.g. "yt-DfECjUL9ZvU.jpg" */
export const thumb = (fileName) => thumbs[`../assets/social/${fileName}`];
