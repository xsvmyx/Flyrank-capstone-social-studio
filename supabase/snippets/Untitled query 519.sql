-- Simuler un utilisateur authentifié
SET LOCAL ROLE authenticated;
SET LOCAL "request.jwt.claim.sub" = '5bdd95fa-3912-4814-b968-0e0282f24dc6';

-- Tester la sélection directe
SELECT * FROM storage.objects WHERE bucket_id = 'post-media';