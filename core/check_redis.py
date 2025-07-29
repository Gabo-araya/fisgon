#!/usr/bin/env python3
#check_redis.py

import redis
import sys

def check_redis():
    try:
        # Intentar conectar
        r = redis.Redis(host='localhost', port=6379, db=0)
        
        # Verificar conexión
        if r.ping():
            print("✅ Redis está funcionando correctamente")
            
            # Mostrar información
            info = r.info()
            print(f"📊 Versión de Redis: {info['redis_version']}")
            print(f"📊 Memoria usada: {info['used_memory_human']}")
            print(f"📊 Clientes conectados: {info['connected_clients']}")
            
            # Limpiar base de datos (opcional)
            response = input("\n¿Deseas limpiar la base de datos de Redis? (s/n): ")
            if response.lower() == 's':
                r.flushdb()
                print("✅ Base de datos limpiada")
            
            return True
    except redis.ConnectionError:
        print("❌ No se puede conectar a Redis")
        print("Intenta: sudo service redis-server start")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    check_redis()