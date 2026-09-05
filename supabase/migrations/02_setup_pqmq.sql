
CREATE EXTENSION IF NOT EXISTS pgmq CASCADE;

SELECT pgmq.create('raw_posts_jobs');

CREATE OR REPLACE FUNCTION enqueue_raw_post_job()
RETURNS TRIGGER 
SECURITY DEFINER
SET search_path = public, pgmq
LANGUAGE plpgsql
AS $$
BEGIN
    PERFORM pgmq.send(
        queue_name => 'raw_posts_jobs',
        msg => jsonb_build_object(
            'post_id', NEW.id,
            'user_id', NEW.user_id,
            'event', 'raw_post.created',
            'created_at', NEW.created_at
        )
    );
    RETURN NEW;
END;
$$;


GRANT USAGE ON SCHEMA pgmq TO postgres, anon, authenticated, service_role;

DROP TRIGGER IF EXISTS trigger_enqueue_raw_post ON public.raw_posts;
CREATE TRIGGER trigger_enqueue_raw_post
    AFTER INSERT ON public.raw_posts
    FOR EACH ROW
    EXECUTE FUNCTION enqueue_raw_post_job();

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