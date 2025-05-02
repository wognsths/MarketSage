"""
InMemoryCache 유틸리티

이 모듈은 애플리케이션 내에서 간단한 캐시 메커니즘을 제공하는 **스레드 안전(Thread-safe) 싱글톤(Singleton) 메모리 캐시 클래스**입니다.

주요 특징:
- 싱글톤 패턴으로 구현되어 애플리케이션 전체에서 단일 인스턴스만 사용됨
- 내부적으로 `dict`를 활용하여 key-value 형식의 캐시 저장
- 항목별 TTL(Time To Live)을 설정하여 일정 시간이 지나면 자동 만료 처리
- 멀티스레드 환경에서도 안전하게 작동하도록 락(Lock) 사용

주요 메서드 설명

1. `__new__`: 싱글톤 패턴 구현을 위한 인스턴스 생성 제어
   - 최초 호출 시 인스턴스를 만들고, 이후부터는 기존 인스턴스를 반환

2. `__init__`: 캐시 저장소 및 TTL 저장소 초기화
   - 실제 초기화는 단 한 번만 수행되며, `_initialized` 플래그로 제어

3. `set(key, value, ttl=None)`:
   - 지정된 key에 데이터를 저장
   - `ttl`(초 단위)을 설정하면 해당 시간이 지나면 자동으로 만료됨

4. `get(key, default=None)`:
   - key에 해당하는 값을 반환
   - 해당 key가 존재하지 않거나 만료된 경우 `default` 반환

5. `delete(key)`:
   - 지정된 key에 해당하는 데이터를 삭제
   - 삭제 성공 시 `True`, 실패 시 `False` 반환

6. `clear()`:
   - 모든 캐시 데이터를 초기화
   - 성공 시 `True` 반환

이 클래스는 세션, 토큰, 임시 결과 등 짧은 기간 동안 유효한 데이터를 빠르게 저장하고 검색하는 데 유용하게 사용할 수 있습니다.
"""

import threading
import time
from typing import Any, Dict, Optional


class InMemoryCache:
    """A thread-safe Singleton class to manage cache data.

    Ensures only one instance of the cache exists across the application.
    """

    _instance: Optional["InMemoryCache"] = None
    _lock: threading.Lock = threading.Lock()
    _initialized: bool = False

    def __new__(cls):
        """Override __new__ to control instance creation (Singleton pattern).

        Uses a lock to ensure thread safety during the first instantiation.

        Returns:
            The singleton instance of InMemoryCache.
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the cache storage.

        Uses a flag (_initialized) to ensure this logic runs only on the very first
        creation of the singleton instance.
        """
        if not self._initialized:
            with self._lock:
                if not self._initialized:
                    # print("Initializing SessionCache storage")
                    self._cache_data: Dict[str, Dict[str, Any]] = {}
                    self._ttl: Dict[str, float] = {}
                    self._data_lock: threading.Lock = threading.Lock()
                    self._initialized = True

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set a key-value pair.

        Args:
            key: The key for the data.
            value: The data to store.
            ttl: Time to live in seconds. If None, data will not expire.
        """
        with self._data_lock:
            self._cache_data[key] = value

            if ttl is not None:
                self._ttl[key] = time.time() + ttl
            else:
                if key in self._ttl:
                    del self._ttl[key]

    def get(self, key: str, default: Any = None) -> Any:
        """Get the value associated with a key.

        Args:
            key: The key for the data within the session.
            default: The value to return if the session or key is not found.

        Returns:
            The cached value, or the default value if not found.
        """
        with self._data_lock:
            if key in self._ttl and time.time() > self._ttl[key]:
                del self._cache_data[key]
                del self._ttl[key]
                return default
            return self._cache_data.get(key, default)

    def delete(self, key: str) -> None:
        """Delete a specific key-value pair from a cache.

        Args:
            key: The key to delete.

        Returns:
            True if the key was found and deleted, False otherwise.
        """

        with self._data_lock:
            if key in self._cache_data:
                del self._cache_data[key]
                if key in self._ttl:
                    del self._ttl[key]
                return True
            return False

    def clear(self) -> bool:
        """Remove all data.

        Returns:
            True if the data was cleared, False otherwise.
        """
        with self._data_lock:
            self._cache_data.clear()
            self._ttl.clear()
            return True
        return False