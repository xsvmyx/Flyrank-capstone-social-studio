-- 1. Detacher temporairement le type de la colonne (ex: table posts)
ALTER TABLE public.posts ALTER COLUMN platform TYPE text;

-- 2. Supprimer l'ENUM
DROP TYPE public.social_platform;

-- 3. Recréer l'ENUM avec les valeurs voulues
CREATE TYPE public.social_platform AS ENUM (
    'linkedin',
    'twitter',
    'instagram',
    'facebook'
);

-- 4. Reconvertir la colonne vers le nouvel ENUM
ALTER TABLE public.posts 
    ALTER COLUMN platform TYPE public.social_platform 
    USING platform::public.social_platform;