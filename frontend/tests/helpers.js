// Giả lập localStorage trong Node để test các hàm đọc/ghi (Node không có sẵn localStorage).
export function installMemoryStorage({ failWrites = false } = {}) {
  const data = new Map();
  globalThis.localStorage = {
    getItem: (k) => (data.has(k) ? data.get(k) : null),
    setItem: (k, v) => {
      if (failWrites) throw new Error('QuotaExceededError');
      data.set(k, String(v));
    },
    removeItem: (k) => data.delete(k),
    clear: () => data.clear(),
  };
  return data;
}

export function removeStorage() {
  delete globalThis.localStorage;
}
