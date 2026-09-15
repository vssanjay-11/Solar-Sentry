import React from 'react';
import { LucideIcon } from 'lucide-react';

interface PanelProps {
  title: string;
  icon?: LucideIcon;
  action?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}

export const Panel: React.FC<PanelProps> = ({ title, icon: Icon, action, children, className = '' }) => {
  return (
    <div className={`glass-panel ${className}`}>
      <div className="panel-heading">
        <div className="heading-label">
          {Icon && <Icon className="heading-icon" />}
          <h2>{title}</h2>
        </div>
        {action}
      </div>
      {children}
    </div>
  );
};

interface StatProps {
  icon: LucideIcon;
  label: string;
  value: string | number;
  detail: string;
  className?: string;
}

export const Stat: React.FC<StatProps> = ({ icon: Icon, label, value, detail, className = '' }) => {
  return (
    <div className={`metric-card ${className}`}>
      <Icon className="metric-icon" />
      <div style={{ minWidth: 0, flex: 1 }}>
        <p className="kicker" style={{ fontSize: '9.5px' }}>{label}</p>
        <div className="metric-value">{value}</div>
        <p className="metric-detail">{detail}</p>
      </div>
    </div>
  );
};

interface ImageStageProps {
  src: string;
  alt: string;
  className?: string;
  timestamp?: string;
  children?: React.ReactNode;
}

export const ImageStage: React.FC<ImageStageProps> = ({
  src,
  alt,
  className = '',
  timestamp,
  children
}) => {
  const displayTime = timestamp || new Date().toISOString().replace('T', ' ').slice(0, 19);

  return (
    <div className={`image-stage ${className}`}>
      <img src={src} alt={alt} />
      <div className="stage-grid" />
      <span className="stage-label">{displayTime}</span>
      {children}
    </div>
  );
};
