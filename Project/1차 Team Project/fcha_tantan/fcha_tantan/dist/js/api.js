const config = window.TANTAN_CONFIG;
export async function loadData() {
  const url = config.mode === 'api' ? `${config.apiBase}/brands/` : new URL('../data/brands.json', import.meta.url);
  const response = await fetch(url, {headers:{Accept:'application/json'}});
  if (!response.ok) throw new Error(`데이터 요청 실패 (${response.status})`);
  const data = await response.json();
  if (!Array.isArray(data.brands) || !Array.isArray(data.years) || !Array.isArray(data.regions)) throw new Error('데이터 형식이 올바르지 않습니다.');
  return data;
}
