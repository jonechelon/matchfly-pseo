/**
 * Perplexity Search Service
 * ==========================
 * 
 * A reusable module for the MatchFly project to get ranked search results
 * from Perplexity's continuously refreshed index with advanced filtering.
 * 
 * Based on Perplexity API /search endpoint:
 * https://api.perplexity.ai/search
 * 
 * Usage:
 *   const searchService = require('./src/perplexity_search_service');
 *   const results = await searchService.search({
 *     query: 'latest AI developments 2024',
 *     max_results: 10,
 *     search_recency_filter: 'week'
 *   });
 */

const https = require('https');

const PERPLEXITY_SEARCH_BASE_URL = 'https://api.perplexity.ai';
const PERPLEXITY_SEARCH_ENDPOINT = '/search';

/**
 * Default API key from environment variables
 * IMPORTANTE: Configure PERPLEXITY_API_KEY ou PPLX_API_KEY como variável de ambiente
 * Em produção, NUNCA use fallback hardcoded
 */
const DEFAULT_API_KEY = process.env.PERPLEXITY_API_KEY || process.env.PPLX_API_KEY;
if (!DEFAULT_API_KEY) {
  throw new Error('PERPLEXITY_API_KEY ou PPLX_API_KEY deve ser configurada como variável de ambiente');
}

/**
 * SearchRequest Schema
 * @typedef {Object} SearchRequest
 * @property {string|string[]} query - Search query or array of queries (max 5)
 * @property {number} [max_results=10] - Max results to return (1-20)
 * @property {number} [max_tokens=25000] - Max tokens across all results (1-1000000)
 * @property {string[]} [search_domain_filter] - Domains to limit results (max 20)
 * @property {number} [max_tokens_per_page=2048] - Max tokens per page
 * @property {string} [country] - Country code filter (e.g., 'US', 'GB', 'DE')
 * @property {'day'|'week'|'month'|'year'} [search_recency_filter] - Recency filter
 * @property {string} [search_after_date] - Format: MM/DD/YYYY (e.g., '10/15/2025')
 * @property {string} [search_before_date] - Format: MM/DD/YYYY (e.g., '10/16/2025')
 * @property {string} [last_updated_after_filter] - Format: MM/DD/YYYY
 * @property {string} [last_updated_before_filter] - Format: MM/DD/YYYY
 * @property {string[]} [search_language_filter] - ISO 639-1 codes (max 10)
 */

/**
 * SearchResult Schema
 * @typedef {Object} SearchResult
 * @property {string} title - Title of the search result
 * @property {string} url - URL of the search result
 * @property {string} snippet - Brief excerpt or summary
 * @property {string} date - Date crawled (YYYY-MM-DD)
 * @property {string} last_updated - Date last updated (YYYY-MM-DD)
 */

/**
 * SearchResponse Schema
 * @typedef {Object} SearchResponse
 * @property {SearchResult[]} results - Array of search results
 */

/**
 * Performs a search request to Perplexity API
 * 
 * @param {SearchRequest} request - Search request parameters
 * @param {string} [apiKey] - Optional API key override
 * @returns {Promise<SearchResponse>} Search results
 * @throws {Error} If request fails or is invalid
 * 
 * @example
 * // Basic search
 * const results = await search({
 *   query: 'latest AI developments 2024',
 *   max_results: 10
 * });
 * 
 * @example
 * // Multi-query search with filters
 * const results = await search({
 *   query: ['AI developments', 'machine learning trends'],
 *   max_results: 20,
 *   search_recency_filter: 'week',
 *   country: 'US',
 *   search_domain_filter: ['science.org', 'pnas.org']
 * });
 */
async function search(request, apiKey = null) {
  const key = apiKey || DEFAULT_API_KEY;

  // Validate required fields
  if (!request || !request.query) {
    throw new Error('SearchRequest must include a query field');
  }

  // Validate query
  if (Array.isArray(request.query)) {
    if (request.query.length === 0) {
      throw new Error('Query array cannot be empty');
    }
    if (request.query.length > 5) {
      throw new Error('Maximum 5 queries allowed in multi-query search');
    }
  } else if (typeof request.query !== 'string' || request.query.trim() === '') {
    throw new Error('Query must be a non-empty string or array of strings');
  }

  // Validate max_results
  if (request.max_results !== undefined) {
    if (!Number.isInteger(request.max_results) || request.max_results < 1 || request.max_results > 20) {
      throw new Error('max_results must be an integer between 1 and 20');
    }
  }

  // Validate max_tokens
  if (request.max_tokens !== undefined) {
    if (!Number.isInteger(request.max_tokens) || request.max_tokens < 1 || request.max_tokens > 1000000) {
      throw new Error('max_tokens must be an integer between 1 and 1000000');
    }
  }

  // Validate search_domain_filter
  if (request.search_domain_filter !== undefined) {
    if (!Array.isArray(request.search_domain_filter) || request.search_domain_filter.length > 20) {
      throw new Error('search_domain_filter must be an array with maximum 20 domains');
    }
  }

  // Validate search_language_filter
  if (request.search_language_filter !== undefined) {
    if (!Array.isArray(request.search_language_filter) || request.search_language_filter.length > 10) {
      throw new Error('search_language_filter must be an array with maximum 10 language codes');
    }
  }

  // Validate search_recency_filter
  const validRecencyFilters = ['day', 'week', 'month', 'year'];
  if (request.search_recency_filter !== undefined) {
    if (!validRecencyFilters.includes(request.search_recency_filter)) {
      throw new Error(`search_recency_filter must be one of: ${validRecencyFilters.join(', ')}`);
    }
  }

  // Build request payload (only include defined fields)
  const payload = {
    query: request.query,
  };

  if (request.max_results !== undefined) payload.max_results = request.max_results;
  if (request.max_tokens !== undefined) payload.max_tokens = request.max_tokens;
  if (request.search_domain_filter !== undefined) payload.search_domain_filter = request.search_domain_filter;
  if (request.max_tokens_per_page !== undefined) payload.max_tokens_per_page = request.max_tokens_per_page;
  if (request.country !== undefined) payload.country = request.country;
  if (request.search_recency_filter !== undefined) payload.search_recency_filter = request.search_recency_filter;
  if (request.search_after_date !== undefined) payload.search_after_date = request.search_after_date;
  if (request.search_before_date !== undefined) payload.search_before_date = request.search_before_date;
  if (request.last_updated_after_filter !== undefined) payload.last_updated_after_filter = request.last_updated_after_filter;
  if (request.last_updated_before_filter !== undefined) payload.last_updated_before_filter = request.last_updated_before_filter;
  if (request.search_language_filter !== undefined) payload.search_language_filter = request.search_language_filter;

  const payloadString = JSON.stringify(payload);

  return new Promise((resolve, reject) => {
    const options = {
      hostname: 'api.perplexity.ai',
      port: 443,
      path: PERPLEXITY_SEARCH_ENDPOINT,
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${key}`,
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(payloadString),
        'User-Agent': 'MatchFly-SearchService/1.0'
      }
    };

    const req = https.request(options, (res) => {
      let data = '';

      res.on('data', (chunk) => {
        data += chunk;
      });

      res.on('end', () => {
        try {
          if (res.statusCode !== 200) {
            let errorMessage = `HTTP ${res.statusCode}`;
            try {
              const errorBody = JSON.parse(data);
              errorMessage = errorBody.error?.message || errorBody.message || errorMessage;
            } catch (e) {
              errorMessage = data || errorMessage;
            }
            reject(new Error(`Perplexity API error: ${errorMessage}`));
            return;
          }

          const response = JSON.parse(data);
          
          // Validate response structure
          if (!response.results || !Array.isArray(response.results)) {
            reject(new Error('Invalid response format: missing results array'));
            return;
          }

          resolve(response);
        } catch (e) {
          reject(new Error(`Failed to parse response: ${e.message}`));
        }
      });
    });

    req.on('error', (error) => {
      reject(new Error(`Request failed: ${error.message}`));
    });

    req.write(payloadString);
    req.end();
  });
}

/**
 * Convenience function for simple single-query searches
 * 
 * @param {string} query - Search query
 * @param {Object} [options] - Additional search options
 * @param {number} [options.max_results=10] - Maximum results
 * @param {'day'|'week'|'month'|'year'} [options.search_recency_filter] - Recency filter
 * @param {string} [apiKey] - Optional API key override
 * @returns {Promise<SearchResponse>} Search results
 */
async function simpleSearch(query, options = {}, apiKey = null) {
  return search({
    query,
    max_results: options.max_results || 10,
    search_recency_filter: options.search_recency_filter,
    ...options
  }, apiKey);
}

module.exports = {
  search,
  simpleSearch
};

// If run directly, perform a test search
if (require.main === module) {
  (async () => {
    try {
      console.log('Testing Perplexity Search Service...\n');
      
      const results = await simpleSearch('latest AI developments 2024', {
        max_results: 5,
        search_recency_filter: 'week'
      });

      console.log(`Found ${results.results.length} results:\n`);
      results.results.forEach((result, index) => {
        console.log(`${index + 1}. ${result.title}`);
        console.log(`   URL: ${result.url}`);
        console.log(`   Date: ${result.date}`);
        console.log(`   Snippet: ${result.snippet.substring(0, 100)}...\n`);
      });
    } catch (error) {
      console.error('Error:', error.message);
      process.exit(1);
    }
  })();
}
