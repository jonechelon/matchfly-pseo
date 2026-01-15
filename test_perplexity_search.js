#!/usr/bin/env node
/**
 * Test script for Perplexity Search Service
 * Tests the search functionality with various parameters
 */

const searchService = require('./src/perplexity_search_service');

async function runTests() {
  console.log('='.repeat(70));
  console.log('🧪 Testing Perplexity Search Service');
  console.log('='.repeat(70));
  console.log('');

  // Test 1: Basic search
  console.log('Test 1: Basic search');
  console.log('-'.repeat(70));
  try {
    const results1 = await searchService.simpleSearch('latest AI developments 2024', {
      max_results: 3
    });
    console.log(`✅ Success: Found ${results1.results.length} results`);
    if (results1.results.length > 0) {
      console.log(`   First result: ${results1.results[0].title}`);
      console.log(`   URL: ${results1.results[0].url}`);
    }
  } catch (error) {
    console.log(`❌ Error: ${error.message}`);
  }
  console.log('');

  // Test 2: Search with recency filter
  console.log('Test 2: Search with recency filter (week)');
  console.log('-'.repeat(70));
  try {
    const results2 = await searchService.search({
      query: 'flight delays compensation',
      max_results: 5,
      search_recency_filter: 'week'
    });
    console.log(`✅ Success: Found ${results2.results.length} results`);
    results2.results.forEach((result, idx) => {
      console.log(`   ${idx + 1}. ${result.title} (${result.date})`);
    });
  } catch (error) {
    console.log(`❌ Error: ${error.message}`);
  }
  console.log('');

  // Test 3: Multi-query search
  console.log('Test 3: Multi-query search');
  console.log('-'.repeat(70));
  try {
    const results3 = await searchService.search({
      query: ['ANAC flight compensation', 'Brazilian airline rights'],
      max_results: 5
    });
    console.log(`✅ Success: Found ${results3.results.length} results`);
  } catch (error) {
    console.log(`❌ Error: ${error.message}`);
  }
  console.log('');

  // Test 4: Search with domain filter
  console.log('Test 4: Search with domain filter');
  console.log('-'.repeat(70));
  try {
    const results4 = await searchService.search({
      query: 'flight compensation',
      max_results: 5,
      search_domain_filter: ['anac.gov.br', 'gov.br']
    });
    console.log(`✅ Success: Found ${results4.results.length} results`);
    if (results4.results.length > 0) {
      results4.results.forEach((result, idx) => {
        console.log(`   ${idx + 1}. ${result.title}`);
        console.log(`      Domain: ${new URL(result.url).hostname}`);
      });
    }
  } catch (error) {
    console.log(`❌ Error: ${error.message}`);
  }
  console.log('');

  // Test 5: Search with country filter
  console.log('Test 5: Search with country filter (Brazil)');
  console.log('-'.repeat(70));
  try {
    const results5 = await searchService.search({
      query: 'flight delays',
      max_results: 3,
      country: 'BR'
    });
    console.log(`✅ Success: Found ${results5.results.length} results`);
  } catch (error) {
    console.log(`❌ Error: ${error.message}`);
  }
  console.log('');

  console.log('='.repeat(70));
  console.log('✅ All tests completed');
  console.log('='.repeat(70));
}

// Run tests
runTests().catch(error => {
  console.error('Fatal error:', error);
  process.exit(1);
});
