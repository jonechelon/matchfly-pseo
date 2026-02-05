#!/usr/bin/env node
/**
 * Header Verification Script
 * Verifies that Authorization headers are correctly formatted and not duplicated
 */

const https = require('https');

// IMPORTANTE: Configure PERPLEXITY_API_KEY como variável de ambiente
const API_KEY = process.env.PERPLEXITY_API_KEY;
if (!API_KEY) {
  console.error('❌ ERRO: PERPLEXITY_API_KEY não está definida como variável de ambiente');
  console.error('   Configure com: export PERPLEXITY_API_KEY="sua-chave-aqui"');
  process.exit(1);
}

console.log('='.repeat(70));
console.log('🔍 Verifying Perplexity API Headers');
console.log('='.repeat(70));
console.log('');

// Test 1: Chat endpoint headers
console.log('Test 1: Chat Endpoint Headers');
console.log('-'.repeat(70));
testChatHeaders();

// Test 2: Search endpoint headers
console.log('\nTest 2: Search Endpoint Headers');
console.log('-'.repeat(70));
testSearchHeaders();

function testChatHeaders() {
  const payload = JSON.stringify({
    model: 'sonar-pro',
    messages: [{ role: 'user', content: 'Say OK' }],
    max_tokens: 5
  });

  const options = {
    hostname: 'api.perplexity.ai',
    port: 443,
    path: '/v1/chat/completions',
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${API_KEY}`,
      'Content-Type': 'application/json',
      'Content-Length': Buffer.byteLength(payload),
      'User-Agent': 'Header-Verification/1.0'
    }
  };

  console.log('Request Headers:');
  console.log(`  Authorization: ${options.headers.Authorization.substring(0, 30)}...`);
  console.log(`  Content-Type: ${options.headers['Content-Type']}`);
  console.log(`  Content-Length: ${options.headers['Content-Length']}`);
  console.log(`  User-Agent: ${options.headers['User-Agent']}`);
  console.log('');
  console.log('✅ Header count:', Object.keys(options.headers).length, '(should be 4, no duplicates)');

  const req = https.request(options, (res) => {
    let data = '';
    res.on('data', (chunk) => { data += chunk; });
    res.on('end', () => {
      console.log(`\nResponse Status: ${res.statusCode}`);
      if (res.statusCode === 200) {
        console.log('✅ Chat endpoint: Headers correctly formatted, request successful');
      } else {
        try {
          const error = JSON.parse(data);
          console.log(`⚠️  Chat endpoint: ${error.error?.message || 'Request failed'}`);
        } catch (e) {
          console.log(`⚠️  Chat endpoint: ${data.substring(0, 100)}`);
        }
      }
    });
  });

  req.on('error', (error) => {
    console.log(`❌ Chat endpoint error: ${error.message}`);
  });

  req.write(payload);
  req.end();
}

function testSearchHeaders() {
  const payload = JSON.stringify({
    query: 'test',
    max_results: 1
  });

  const options = {
    hostname: 'api.perplexity.ai',
    port: 443,
    path: '/search',
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${API_KEY}`,
      'Content-Type': 'application/json',
      'Content-Length': Buffer.byteLength(payload),
      'User-Agent': 'Header-Verification/1.0'
    }
  };

  console.log('Request Headers:');
  console.log(`  Authorization: ${options.headers.Authorization.substring(0, 30)}...`);
  console.log(`  Content-Type: ${options.headers['Content-Type']}`);
  console.log(`  Content-Length: ${options.headers['Content-Length']}`);
  console.log(`  User-Agent: ${options.headers['User-Agent']}`);
  console.log('');
  console.log('✅ Header count:', Object.keys(options.headers).length, '(should be 4, no duplicates)');

  const req = https.request(options, (res) => {
    let data = '';
    res.on('data', (chunk) => { data += chunk; });
    res.on('end', () => {
      console.log(`\nResponse Status: ${res.statusCode}`);
      if (res.statusCode === 200) {
        console.log('✅ Search endpoint: Headers correctly formatted, request successful');
      } else {
        try {
          const error = JSON.parse(data);
          console.log(`⚠️  Search endpoint: ${error.error?.message || 'Request failed'}`);
        } catch (e) {
          console.log(`⚠️  Search endpoint: ${data.substring(0, 100)}`);
        }
      }
    });
  });

  req.on('error', (error) => {
    console.log(`❌ Search endpoint error: ${error.message}`);
  });

  req.write(payload);
  req.end();
}
