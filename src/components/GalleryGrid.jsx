const GalleryGrid = ({ photos, eventId }) => {
  if (!photos || photos.length === 0) return null;

  return (
    <div className="mt-3">
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
        {photos.map((photo, idx) => (
          <a
            key={idx}
            href={photo}
            target="_blank"
            rel="noopener noreferrer"
            className="block rounded-lg overflow-hidden bg-elevated hover:opacity-90 transition-opacity"
          >
            <img
              src={photo}
              alt={`Photo ${idx + 1} from event`}
              className="w-full h-24 sm:h-28 object-cover"
              loading="lazy"
            />
          </a>
        ))}
      </div>
    </div>
  );
};

export default GalleryGrid;
