// backend/server.js — Express API Gateway
import 'dotenv/config';
import express from 'express';
import { PrismaClient } from './generated/prisma/client.ts';
import { PrismaPg } from '@prisma/adapter-pg';
import pg from 'pg';
import axios from 'axios';

const app = express();

// Prisma adapter setup (see prisma.config.ts for datasource URL)
const pool = new pg.Pool({ connectionString: process.env.DATABASE_URL });
const adapter = new PrismaPg(pool);
const prisma = new PrismaClient({ adapter });

const PORT = process.env.PORT || 5005;
const ML_URL = process.env.ML_SERVICE_URL || 'http://localhost:8000';

// Manual CORS
app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', '*');
  res.header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  res.header('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  if (req.method === 'OPTIONS') return res.sendStatus(204);
  next();
});

app.use(express.json());

// ── Helpers ──

async function getDbStats() {
  // Aggregate ratings: group by pg_id
  const ratingAgg = await prisma.rating.groupBy({
    by: ['pg_id'],
    _avg: { rating: true },
    _count: { rating: true },
  });
  const ratings = {};
  for (const r of ratingAgg) {
    ratings[r.pg_id] = {
      average_rating: r._avg.rating !== null ? parseFloat(r._avg.rating.toFixed(2)) : 3.5,
      rating_count: r._count.rating,
    };
  }

  // Aggregate reviews: group by pg_id
  const reviewAgg = await prisma.review.groupBy({
    by: ['pg_id'],
    _avg: { sentiment_score: true },
    _count: { sentiment_score: true },
  });
  const reviews = {};
  for (const r of reviewAgg) {
    reviews[r.pg_id] = {
      avg_sentiment: r._avg.sentiment_score !== null ? parseFloat(r._avg.sentiment_score.toFixed(4)) : 0.5,
      review_count: r._count.sentiment_score,
    };
  }

  return { ratings, reviews };
}

// ── POST /api/recommendations ──
app.post('/api/recommendations', async (req, res) => {
  try {
    const userPreferences = req.body;

    // Fetch db_stats from Prisma
    const dbStats = await getDbStats();

    // Call ML service
    const mlResponse = await axios.post(`${ML_URL}/recommend`, {
      user_preferences: userPreferences,
      db_stats: dbStats,
    });

    return res.json(mlResponse.data);
  } catch (err) {
    console.error('POST /api/recommendations error:', err.message);
    if (err.code === 'ECONNREFUSED') {
      return res.status(503).json({
        error: 'ML service is not available. Please ensure the recommendation engine is running.',
        results: [],
      });
    }
    return res.status(500).json({
      error: 'Something went wrong while fetching recommendations.',
      results: [],
    });
  }
});

// ── POST /api/rate-pg ──
app.post('/api/rate-pg', async (req, res) => {
  try {
    const { pg_id, rating } = req.body;

    if (pg_id == null || rating == null) {
      return res.status(400).json({ error: 'pg_id and rating are required' });
    }
    if (rating < 1 || rating > 5) {
      return res.status(422).json({ error: 'Rating must be between 1 and 5' });
    }

    // Save rating
    await prisma.rating.create({
      data: { pg_id: Number(pg_id), rating: Number(rating) },
    });

    // Fetch updated stats
    const agg = await prisma.rating.aggregate({
      where: { pg_id: Number(pg_id) },
      _avg: { rating: true },
      _count: { rating: true },
    });

    return res.json({
      success: true,
      pg_id: Number(pg_id),
      average_rating: agg._avg.rating !== null ? parseFloat(agg._avg.rating.toFixed(2)) : 3.5,
      rating_count: agg._count.rating,
    });
  } catch (err) {
    console.error('POST /api/rate-pg error:', err.message);
    return res.status(500).json({ error: 'Failed to save rating.' });
  }
});

// ── POST /api/submit-review ──
app.post('/api/submit-review', async (req, res) => {
  try {
    const { pg_id, review_text } = req.body;

    if (pg_id == null || !review_text || !review_text.trim()) {
      return res.status(400).json({ error: 'pg_id and review_text are required' });
    }

    // Call ML service for sentiment analysis
    const mlResponse = await axios.post(`${ML_URL}/analyze-sentiment`, {
      review_text: review_text.trim(),
    });
    const { sentiment_score } = mlResponse.data;

    // Save review
    await prisma.review.create({
      data: {
        pg_id: Number(pg_id),
        review_text: review_text.trim(),
        sentiment_score,
      },
    });

    // Fetch updated stats
    const pgId = Number(pg_id);
    const allReviews = await prisma.review.findMany({
      where: { pg_id: pgId },
      orderBy: { id: 'asc' },
    });

    const reviewCount = allReviews.length;
    const avgSentiment =
      reviewCount > 0
        ? parseFloat(
            (allReviews.reduce((sum, r) => sum + r.sentiment_score, 0) / reviewCount).toFixed(4)
          )
        : 0.5;

    function getLabel(score) {
      if (score >= 0.9) return 'Excellent';
      if (score >= 0.6) return 'Good';
      if (score >= 0.4) return 'Average';
      return 'Poor';
    }

    function starEquivalent(score) {
      return parseFloat((1.0 + score * 4.0).toFixed(2));
    }

    const reviews = allReviews.map((r) => ({
      text: r.review_text,
      sentiment_score: r.sentiment_score,
      sentiment_label: getLabel(r.sentiment_score),
    }));

    return res.json({
      success: true,
      pg_id: pgId,
      sentiment_score,
      sentiment_label: getLabel(sentiment_score),
      star_equivalent: starEquivalent(sentiment_score),
      avg_sentiment: avgSentiment,
      review_count: reviewCount,
      reviews: reviews.slice(-5),
    });
  } catch (err) {
    console.error('POST /api/submit-review error:', err.message);
    if (err.code === 'ECONNREFUSED') {
      return res.status(503).json({ error: 'ML service is not available for sentiment analysis.' });
    }
    return res.status(500).json({ error: 'Failed to submit review.' });
  }
});

// ── GET /api/reviews/:pgId ──
app.get('/api/reviews/:pgId', async (req, res) => {
  try {
    const pgId = Number(req.params.pgId);

    const allReviews = await prisma.review.findMany({
      where: { pg_id: pgId },
      orderBy: { id: 'asc' },
    });

    const reviewCount = allReviews.length;
    const avgSentiment =
      reviewCount > 0
        ? parseFloat(
            (allReviews.reduce((sum, r) => sum + r.sentiment_score, 0) / reviewCount).toFixed(4)
          )
        : 0.5;

    function getLabel(score) {
      if (score >= 0.9) return 'Excellent';
      if (score >= 0.6) return 'Good';
      if (score >= 0.4) return 'Average';
      return 'Poor';
    }

    const reviews = allReviews.map((r) => ({
      id: r.id,
      text: r.review_text,
      sentiment_score: r.sentiment_score,
      sentiment_label: getLabel(r.sentiment_score),
    }));

    return res.json({
      success: true,
      pg_id: pgId,
      reviews: reviews.slice(-20),
      avg_sentiment: avgSentiment,
      review_count: reviewCount,
    });
  } catch (err) {
    console.error('GET /api/reviews/:pgId error:', err.message);
    return res.status(500).json({ error: 'Failed to fetch reviews.' });
  }
});

// ── Health check ──
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', service: 'express-gateway' });
});

app.listen(PORT, () => {
  console.log(`🚀 Express Gateway running on http://localhost:${PORT}`);
});
