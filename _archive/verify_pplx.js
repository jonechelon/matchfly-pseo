#!/usr/bin/env node
/**
 * Perplexity API Verification Script
 * Tests connectivity and model access using the same configuration as Cursor
 */

const https = require('https');

// Configuração - O script tentará ler do seu terminal
// IMPORTANTE: Configure PERPLEXITY_API_KEY como variável de ambiente
const API_KEY = process.env.PERPLEXITY_API_KEY;
if (!API_KEY) {
  console.error('❌ ERRO: PERPLEXITY_API_KEY não está definida como variável de ambiente');
  console.error('   Configure com: export PERPLEXITY_API_KEY="sua-chave-aqui"');
  process.exit(1);
}
const BASE_URL = 'https://api.perplexity.ai/v1';

// Modelos que vamos validar (apenas modelos válidos para chat)
const MODELS_TO_TEST = [
  'sonar',
  'sonar-pro'
];

function makeRequest(path, method = 'GET', body = null) {
  return new Promise((resolve, reject) => {
    const url = new URL(path, BASE_URL);
    
    const options = {
      hostname: url.hostname,
      port: 443,
      path: url.pathname + url.search,
      method: method,
      headers: {
        'Authorization': `Bearer ${API_KEY}`,
        'Content-Type': 'application/json',
        'User-Agent': 'Cursor-Verification-Script/1.0'
      }
    };

    if (body) {
      options.headers['Content-Length'] = Buffer.byteLength(body);
    }

    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', (chunk) => { data += chunk; });
      res.on('end', () => {
        try {
          const parsed = JSON.parse(data);
          resolve({ status: res.statusCode, body: parsed });
        } catch (e) {
          resolve({ status: res.statusCode, body: data });
        }
      });
    });

    req.on('error', (error) => { reject(error); });
    if (body) { req.write(body); }
    req.end();
  });
}

async function main() {
  console.log('='.repeat(60));
  console.log('Iniciando Verificação da API Perplexity');
  console.log(`Endpoint: ${BASE_URL}`);
  console.log('='.repeat(60));

  // Teste 1: Listar modelos disponíveis
  console.log('\n🔍 Testando endpoint /models...');
  const resModels = await makeRequest('/models');
  console.log(`Status: ${resModels.status}`);
  
  // Teste 2: Testar cada modelo individualmente
  for (const model of MODELS_TO_TEST) {
    console.log(`\n🧪 Testando modelo: ${model}`);
    const payload = JSON.stringify({
      model: model,
      messages: [{ role: 'user', content: 'Responder apenas com "OK"' }],
      max_tokens: 10
    });

    try {
      const res = await makeRequest('/chat/completions', 'POST', payload);
      if (res.status === 200) {
        console.log(`✅ SUCESSO: O modelo "${model}" está funcionando.`);
      } else {
        console.log(`❌ FALHA: Status ${res.status} para o modelo "${model}".`);
        if (res.body.error) console.log(`   Erro: ${res.body.error.message}`);
      }
    } catch (e) {
      console.log(`❌ ERRO de conexão para ${model}: ${e.message}`);
    }
    // Pequena pausa para evitar rate limit durante o teste
    await new Promise(r => setTimeout(r, 500));
  }
}

main().catch(console.error);