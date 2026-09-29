CREATE EXTENSION IF NOT EXISTS pgmq CASCADE;


SELECT pgmq.create('background_jobs');

GRANT USAGE ON SCHEMA pgmq TO postgres, anon, authenticated, service_role;


CREATE OR REPLACE FUNCTION public.pgmq_read(queue_name text, vt integer, qty integer)
RETURNS TABLE (
    msg_id bigint,
    read_ct integer,
    enqueued_at timestamptz,
    vt_at timestamptz,
    message jsonb
) 
SECURITY DEFINER
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY 
    SELECT r.msg_id, r.read_ct, r.enqueued_at, r.vt, r.message 
    FROM pgmq.read(queue_name, vt, qty) AS r;
END;
$$;

CREATE OR REPLACE FUNCTION public.pgmq_delete(queue_name text, msg_id bigint)
RETURNS boolean 
SECURITY DEFINER
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN pgmq.delete(queue_name, msg_id);
END;
$$;

CREATE OR REPLACE FUNCTION public.pgmq_send(queue_name text, msg jsonb)
RETURNS bigint 
SECURITY DEFINER
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN pgmq.send(queue_name, msg);
END;
$$;


CREATE OR REPLACE FUNCTION public.enqueue_variant_job(p_post_id uuid, p_platform text)
RETURNS bigint 
SECURITY DEFINER
LANGUAGE plpgsql
AS $$
DECLARE
    v_msg_id bigint;
BEGIN
    v_msg_id := pgmq.send(
        queue_name => 'background_jobs',
        msg => jsonb_build_object(
            'event', 'variant.generate',
            'payload', jsonb_build_object(
                'post_id', p_post_id,
                'platform', p_platform
            )
        )
    );
    RETURN v_msg_id;
END;
$$;