export async function onRequest(context) {
  const backend = 'https://tianwen-agi-production-fa3e.up.railway.app';
  const response = await fetch(backend + '/api/health');
  const newResponse = new Response(response.body, response);
  newResponse.headers.set('Access-Control-Allow-Origin', '*');
  return newResponse;
}
