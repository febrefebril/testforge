SELECT hs.* FROM healing_suggestion hs LEFT JOIN review_decision rd ON rd.healing_suggestion_id=hs.id WHERE hs.mode='shadow' AND rd.id IS NULL ORDER BY hs.created_at DESC LIMIT 100;
