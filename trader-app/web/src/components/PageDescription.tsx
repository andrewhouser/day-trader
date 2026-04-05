import styles from "./PageDescription.module.css";

interface Props {
  title: string;
  children: React.ReactNode;
}

export function PageDescription({ title, children }: Props) {
  return (
    <div className={styles.wrapper}>
      <div className={styles.title}>{title}</div>
      <div className={styles.body}>{children}</div>
    </div>
  );
}
