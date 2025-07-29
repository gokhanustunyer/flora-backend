import asyncio
import asyncpg
import os
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv()

async def test_supabase_connection():
    """Supabase PostgreSQL bağlantısını test et"""
    
    # Farklı connection string formatları dene
    connection_strings = [
        # Supabase Pooler (6543 port) - Önerilen
        "postgresql://postgres.fizhsiptciksjawsycvg:flora2025.@aws-0-eu-central-1.pooler.supabase.com:6543/postgres",
        
        # Direkt host kullanarak (5432 port)
        "postgresql://postgres:flora2025.@fizhsiptciksjawsycvg.supabase.co:5432/postgres",
        
        # db prefix ile
        "postgresql://postgres:flora2025.@db.fizhsiptciksjawsycvg.supabase.co:5432/postgres"
    ]
    
    for i, conn_str in enumerate(connection_strings, 1):
        print(f"\n--- Test {i}: {conn_str[:50]}... ---")
        try:
            # Timeout ekle
            conn = await asyncio.wait_for(
                asyncpg.connect(conn_str.replace('+asyncpg', '')), 
                timeout=10.0
            )
            print("✅ Bağlantı başarılı!")
            
            # Basit bir sorgu çalıştır
            result = await conn.fetchval("SELECT version()")
            print(f"📊 PostgreSQL Sürümü: {result[:50]}...")
            
            await conn.close()
            print("🔌 Bağlantı kapatıldı")
            return True
            
        except asyncio.TimeoutError:
            print("❌ Timeout: Bağlantı 10 saniye içinde kurulamadı")
        except Exception as e:
            print(f"❌ Hata: {type(e).__name__}: {e}")
    
    return False


async def test_network_connectivity():
    """Ağ bağlantısını test et"""
    import socket
    
    print("\n=== AĞ BAĞLANTISI TESTI ===")
    
    hosts_to_test = [
        ("aws-0-eu-central-1.pooler.supabase.com", 6543),  # Pooler
        ("fizhsiptciksjawsycvg.supabase.co", 5432),
        ("db.fizhsiptciksjawsycvg.supabase.co", 5432),
        ("google.com", 80)
    ]
    
    for host, port in hosts_to_test:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                print(f"✅ {host}:{port} - Erişilebilir")
            else:
                print(f"❌ {host}:{port} - Erişilemiyor (Error: {result})")
        except Exception as e:
            print(f"❌ {host}:{port} - Hata: {e}")


async def main():
    print("🔍 SUPABASE BAĞLANTI TESTİ BAŞLADI")
    print("=" * 50)
    
    # Ağ testi
    await test_network_connectivity()
    
    # Veritabanı bağlantı testi
    print("\n=== VERİTABANI BAĞLANTI TESTİ ===")
    success = await test_supabase_connection()
    
    if success:
        print("\n🎉 Test tamamlandı - Bağlantı başarılı!")
    else:
        print("\n❌ Test tamamlandı - Tüm bağlantı denemeleri başarısız!")
        print("\n🔧 ÖNERİLER:")
        print("1. Supabase projenizin aktif olduğunu kontrol edin")
        print("2. Veritabanı şifrenizin doğru olduğunu kontrol edin")
        print("3. IP adresinizin Supabase'de beyaz listeye alındığını kontrol edin")
        print("4. Farklı bir ağdan (mobil hotspot) test edin")

if __name__ == "__main__":
    asyncio.run(main())