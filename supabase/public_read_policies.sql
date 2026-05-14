-- Public read policies for the AIFIA frontend.
-- Run this in Supabase SQL Editor if the app uses a publishable/anon key.
-- Import/admin scripts should continue to use the service-role key server-side.

ALTER TABLE public.companies ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.financial_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.price_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.analysis_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.kronos_predictions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.company_highlights ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "public read companies" ON public.companies;
CREATE POLICY "public read companies"
ON public.companies
FOR SELECT
TO anon
USING (true);

DROP POLICY IF EXISTS "public read financial reports" ON public.financial_reports;
CREATE POLICY "public read financial reports"
ON public.financial_reports
FOR SELECT
TO anon
USING (true);

DROP POLICY IF EXISTS "public read price history" ON public.price_history;
CREATE POLICY "public read price history"
ON public.price_history
FOR SELECT
TO anon
USING (true);

DROP POLICY IF EXISTS "public read analysis results" ON public.analysis_results;
CREATE POLICY "public read analysis results"
ON public.analysis_results
FOR SELECT
TO anon
USING (true);

DROP POLICY IF EXISTS "public read kronos predictions" ON public.kronos_predictions;
CREATE POLICY "public read kronos predictions"
ON public.kronos_predictions
FOR SELECT
TO anon
USING (true);

DROP POLICY IF EXISTS "public read company highlights" ON public.company_highlights;
CREATE POLICY "public read company highlights"
ON public.company_highlights
FOR SELECT
TO anon
USING (true);
