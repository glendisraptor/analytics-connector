interface SupersetEmbedProps {
    dashboardId?: number;
    height?: string;
    supersetUrl: string;
}

const SupersetEmbed: React.FC<SupersetEmbedProps> = ({
    dashboardId,
    height = '600px',
    supersetUrl
}) => {
    const embedUrl = dashboardId
        ? `${supersetUrl}/superset/dashboard/${dashboardId}/?standalone=true`
        : `${supersetUrl}/sqllab/`;

    return (
        <div className="w-full border rounded-lg overflow-hidden">
            <iframe
                src={embedUrl}
                width="100%"
                height={height}
                frameBorder="0"
                title="Superset Analytics"
                className="w-full"
            />
        </div>
    );
};

export default SupersetEmbed;