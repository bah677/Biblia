import logging
from typing import List, Dict, Optional
from .database import Database

logger = logging.getLogger(__name__)

class ReferralStorage:
    def __init__(self, database: Database):
        self.db = database
    
    async def add_referral(self, referrer_id: int, referral_id: int, referral_code: str = None) -> bool:
        """Добавляет реферальную связь"""
        try:
            async with self.db.get_connection() as conn:
                # Проверяем, не был ли уже referral_id кем-то приглашен
                existing = await conn.fetchval(
                    'SELECT 1 FROM referrals WHERE referral_id = $1',
                    referral_id
                )
                
                if existing:
                    logger.info(f"⚠️ Referral {referral_id} already exists")
                    return False
                
                await conn.execute('''
                    INSERT INTO referrals (referrer_id, referral_id, referral_code)
                    VALUES ($1, $2, $3)
                ''', referrer_id, referral_id, referral_code)
                
                logger.info(f"✅ Referral added: {referral_id} -> {referrer_id}")
                return True
        except Exception as e:
            logger.error(f"❌ Failed to add referral: {e}")
            return False
    
    async def get_referrer(self, referral_id: int) -> Optional[int]:
        """Получает ID реферера по ID реферала"""
        try:
            async with self.db.get_connection() as conn:
                referrer_id = await conn.fetchval(
                    'SELECT referrer_id FROM referrals WHERE referral_id = $1',
                    referral_id
                )
                return referrer_id
        except Exception as e:
            logger.error(f"❌ Failed to get referrer for {referral_id}: {e}")
            return None
    
    async def get_referrals_count(self, referrer_id: int) -> int:
        """Получает количество рефералов у пользователя"""
        try:
            async with self.db.get_connection() as conn:
                count = await conn.fetchval(
                    'SELECT COUNT(*) FROM referrals WHERE referrer_id = $1',
                    referrer_id
                )
                return count
        except Exception as e:
            logger.error(f"❌ Failed to get referrals count for {referrer_id}: {e}")
            return 0
    
    async def get_referral_stats(self, referrer_id: int) -> Dict:
        """Получает статистику рефералов"""
        try:
            async with self.db.get_connection() as conn:
                # Общее количество рефералов
                total_count = await conn.fetchval(
                    'SELECT COUNT(*) FROM referrals WHERE referrer_id = $1',
                    referrer_id
                )
                
                # Рефералы за последние 30 дней
                recent_count = await conn.fetchval('''
                    SELECT COUNT(*) FROM referrals 
                    WHERE referrer_id = $1 AND created_at >= NOW() - INTERVAL '30 days'
                ''', referrer_id)
                
                # Последние рефералы
                recent_referrals = await conn.fetch('''
                    SELECT r.referral_id, u.first_name, u.username, r.created_at
                    FROM referrals r
                    LEFT JOIN users u ON r.referral_id = u.user_id
                    WHERE r.referrer_id = $1
                    ORDER BY r.created_at DESC
                    LIMIT 10
                ''', referrer_id)
                
                return {
                    'total_count': total_count,
                    'recent_count': recent_count,
                    'recent_referrals': [dict(row) for row in recent_referrals]
                }
        except Exception as e:
            logger.error(f"❌ Failed to get referral stats for {referrer_id}: {e}")
            return {}