type StitchReferenceCardProps = {
  screenId: string;
  title: string;
  htmlFile: string;
  imageFile: string;
  routeScope: string;
};

export function StitchReferenceCard({ screenId, title, htmlFile, imageFile, routeScope }: StitchReferenceCardProps) {
  return (
    <section className="rounded-xl border border-slate-700 bg-slate-900/70 p-4">
      <p className="text-xs uppercase tracking-wide text-slate-400">Stitch Reference</p>
      <h2 className="mt-1 text-lg font-semibold text-white">{title}</h2>
      <div className="mt-3 space-y-1 text-sm text-slate-300">
        <p>
          <span className="text-slate-400">Route scope:</span> {routeScope}
        </p>
        <p>
          <span className="text-slate-400">Screen ID:</span> {screenId}
        </p>
        <p>
          <span className="text-slate-400">HTML:</span> {htmlFile}
        </p>
        <p>
          <span className="text-slate-400">Image:</span> {imageFile}
        </p>
      </div>
    </section>
  );
}
