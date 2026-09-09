ALTER TYPE public.variant_status
    RENAME VALUE 'pending' TO 'draft';

ALTER TYPE public.variant_status
    RENAME VALUE 'completed' TO 'approved';

ALTER TYPE public.variant_status
    RENAME VALUE 'failed' TO 'rejected';