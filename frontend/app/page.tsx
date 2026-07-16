export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <div className="z-10 max-w-5xl w-full items-center justify-center font-mono text-sm flex flex-col gap-8">
        <h1 className="text-4xl font-bold tracking-tight">IQoCreator</h1>
        <p className="text-lg text-muted-foreground">
          AI-powered research platform
        </p>
        <div className="flex gap-4 mt-4">
          <div className="rounded-lg border bg-card text-card-foreground shadow-sm p-6">
            <p className="text-sm text-muted-foreground">API Status</p>
            <p className="text-2xl font-semibold mt-2" id="api-status">
              Checking...
            </p>
          </div>
        </div>
      </div>
    </main>
  );
}
